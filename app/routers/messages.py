from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user, check_block
from app.models.user import User
from app.models.match import Match
from app.models.message import DirectMessage
from app.schemas.message import SendMessageRequest, MessageResponse

router = APIRouter()


def _validate_match_membership(db: Session, match_id: str, user_id: str) -> Match:
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if user_id not in (match.user1_id, match.user2_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your match")
    return match




@router.get("/{match_id}/messages", response_model=list[MessageResponse])
def get_messages(
    match_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = _validate_match_membership(db, match_id, current_user.id)

    other_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
    check_block(db, current_user.id, other_id, detail="Cannot view messages with blocked user")

    messages = (
        db.query(DirectMessage)
        .filter(DirectMessage.match_id == match_id)
        .order_by(DirectMessage.created_at)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{match_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    match_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = _validate_match_membership(db, match_id, current_user.id)

    # Check block between the two users in the match
    other_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
    check_block(db, current_user.id, other_id, detail="Cannot message blocked user")

    message = DirectMessage(
        match_id=match_id,
        sender_id=current_user.id,
        content=request.content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return MessageResponse.model_validate(message)
