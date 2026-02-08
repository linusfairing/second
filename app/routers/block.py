import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.match import Like, Match
from app.models.message import DirectMessage
from app.models.block import BlockedUser
from app.schemas.block import BlockRequest, BlockResponse, BlockedUserResponse, BlockedUserListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=BlockResponse, status_code=status.HTTP_201_CREATED)
def block_user(
    request: BlockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.blocked_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot block yourself")

    target = db.query(User).filter(User.id == request.blocked_user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = db.query(BlockedUser).filter(
        BlockedUser.blocker_id == current_user.id,
        BlockedUser.blocked_id == request.blocked_user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already blocked")

    block = BlockedUser(blocker_id=current_user.id, blocked_id=request.blocked_user_id)
    db.add(block)

    # Clean up likes between the two users
    db.query(Like).filter(
        ((Like.liker_id == current_user.id) & (Like.liked_id == request.blocked_user_id))
        | ((Like.liker_id == request.blocked_user_id) & (Like.liked_id == current_user.id))
    ).delete(synchronize_session="fetch")

    # Auto-unmatch
    auto_unmatched = False
    user1 = min(current_user.id, request.blocked_user_id)
    user2 = max(current_user.id, request.blocked_user_id)
    match = db.query(Match).filter(Match.user1_id == user1, Match.user2_id == user2).first()
    if match:
        db.query(DirectMessage).filter(DirectMessage.match_id == match.id).delete()
        db.delete(match)
        auto_unmatched = True

    db.commit()
    logger.info("User %s blocked %s (auto_unmatched=%s)", current_user.id, request.blocked_user_id, auto_unmatched)

    return BlockResponse(blocked_user_id=request.blocked_user_id, auto_unmatched=auto_unmatched)


@router.delete("/{blocked_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unblock_user(
    blocked_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    block = db.query(BlockedUser).filter(
        BlockedUser.blocker_id == current_user.id,
        BlockedUser.blocked_id == blocked_user_id,
    ).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    db.delete(block)
    db.commit()
    logger.info("User %s unblocked %s", current_user.id, blocked_user_id)


@router.get("", response_model=BlockedUserListResponse)
def list_blocked_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(BlockedUser).filter(BlockedUser.blocker_id == current_user.id)
    total = query.count()
    blocks = (
        query
        .order_by(BlockedUser.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return BlockedUserListResponse(
        blocks=[
            BlockedUserResponse(id=b.id, blocked_user_id=b.blocked_id, created_at=b.created_at)
            for b in blocks
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
