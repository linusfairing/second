import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user, check_block
from app.models.user import User
from app.models.profile import UserProfile
from app.models.match import Like, Match
from app.models.message import DirectMessage
from app.schemas.match import LikeRequest, LikeResponse, PassRequest, PassResponse, MatchResponse, MatchListResponse
from app.services.matching_service import calculate_compatibility
from app.utils.profile_builder import build_discover_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/like", response_model=LikeResponse)
def like_user(
    request: LikeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.liked_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot like yourself")

    target = db.query(User).filter(User.id == request.liked_user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not target.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot like a deactivated user")

    check_block(db, current_user.id, request.liked_user_id)

    existing = db.query(Like).filter(
        Like.liker_id == current_user.id, Like.liked_id == request.liked_user_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already liked/passed this user")

    like = Like(liker_id=current_user.id, liked_id=request.liked_user_id, is_pass=False)
    db.add(like)

    # Check for mutual like (same transaction — nothing committed yet)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already liked/passed this user")

    mutual = db.query(Like).filter(
        Like.liker_id == request.liked_user_id,
        Like.liked_id == current_user.id,
        Like.is_pass == False,  # noqa: E712
    ).first()

    match_id = None
    is_match = False

    if mutual:
        user1 = min(current_user.id, request.liked_user_id)
        user2 = max(current_user.id, request.liked_user_id)

        existing_match = db.query(Match).filter(
            Match.user1_id == user1, Match.user2_id == user2
        ).first()

        if not existing_match:
            my_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
            their_profile = db.query(UserProfile).filter(UserProfile.user_id == request.liked_user_id).first()
            score = calculate_compatibility(my_profile, their_profile)

            match = Match(user1_id=user1, user2_id=user2, compatibility_score=round(score, 4))
            db.add(match)
            db.flush()
            match_id = match.id
            is_match = True

    db.commit()
    return LikeResponse(liked_user_id=request.liked_user_id, is_match=is_match, match_id=match_id)


@router.post("/pass", response_model=PassResponse)
def pass_user(
    request: PassRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.passed_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot pass yourself")

    target = db.query(User).filter(User.id == request.passed_user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    check_block(db, current_user.id, request.passed_user_id)

    existing = db.query(Like).filter(
        Like.liker_id == current_user.id, Like.liked_id == request.passed_user_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already liked/passed this user")

    like = Like(liker_id=current_user.id, liked_id=request.passed_user_id, is_pass=True)
    db.add(like)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already liked/passed this user")

    return PassResponse(passed_user_id=request.passed_user_id)


@router.get("", response_model=MatchListResponse)
def list_matches(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Match).filter(
        (Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)
    ).order_by(Match.created_at.desc())

    total = query.count()
    matches_page = query.offset(offset).limit(limit).all()

    # Batch-load all other users in one query to avoid N+1
    other_ids = [
        m.user2_id if m.user1_id == current_user.id else m.user1_id
        for m in matches_page
    ]
    if other_ids:
        others = db.query(User).filter(User.id.in_(other_ids)).all()
        others_by_id = {u.id: u for u in others}
    else:
        others_by_id = {}

    results = []
    for m in matches_page:
        other_id = m.user2_id if m.user1_id == current_user.id else m.user1_id
        other_user = others_by_id.get(other_id)
        if other_user:
            score = m.compatibility_score or 0.0
            results.append(MatchResponse(
                id=m.id,
                other_user=build_discover_user(other_user, score),
                compatibility_score=m.compatibility_score,
                created_at=m.created_at,
            ))

    return MatchListResponse(matches=results, total=total, limit=limit, offset=offset)


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def unmatch(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    if current_user.id not in (match.user1_id, match.user2_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your match")

    # Delete associated messages and likes between the two users
    db.query(DirectMessage).filter(DirectMessage.match_id == match_id).delete()
    db.query(Like).filter(
        ((Like.liker_id == match.user1_id) & (Like.liked_id == match.user2_id))
        | ((Like.liker_id == match.user2_id) & (Like.liked_id == match.user1_id))
    ).delete(synchronize_session="fetch")
    db.delete(match)
    db.commit()
