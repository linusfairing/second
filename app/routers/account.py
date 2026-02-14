import logging
from pathlib import Path
from shutil import rmtree

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.match import Like, Match
from app.models.message import DirectMessage
from app.models.block import BlockedUser
from app.models.conversation import ConversationMessage, ConversationState
from app.schemas.account import AccountStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/deactivate", response_model=AccountStatusResponse)
def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.is_active = False
    db.commit()
    db.refresh(current_user)
    logger.info("Account deactivated: %s", current_user.email)
    return AccountStatusResponse(is_active=current_user.is_active, email=current_user.email, created_at=current_user.created_at)


@router.post("/reactivate", response_model=AccountStatusResponse)
def reactivate_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.is_active = True
    db.commit()
    db.refresh(current_user)
    logger.info("Account reactivated: %s", current_user.email)
    return AccountStatusResponse(is_active=current_user.is_active, email=current_user.email, created_at=current_user.created_at)


@router.get("/status", response_model=AccountStatusResponse)
def account_status(current_user: User = Depends(get_current_user)):
    return AccountStatusResponse(is_active=current_user.is_active, email=current_user.email, created_at=current_user.created_at)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = current_user.id
    email = current_user.email  # Capture before delete (avoids DetachedInstanceError)

    # Delete messages in matches involving this user
    match_ids = [
        m.id for m in db.query(Match.id).filter(
            (Match.user1_id == uid) | (Match.user2_id == uid)
        ).all()
    ]
    if match_ids:
        db.query(DirectMessage).filter(DirectMessage.match_id.in_(match_ids)).delete(synchronize_session="fetch")

    # Delete matches, likes, blocks, conversations
    db.query(Match).filter((Match.user1_id == uid) | (Match.user2_id == uid)).delete(synchronize_session="fetch")
    db.query(Like).filter((Like.liker_id == uid) | (Like.liked_id == uid)).delete(synchronize_session="fetch")
    db.query(BlockedUser).filter((BlockedUser.blocker_id == uid) | (BlockedUser.blocked_id == uid)).delete(synchronize_session="fetch")
    db.query(ConversationMessage).filter(ConversationMessage.user_id == uid).delete(synchronize_session="fetch")
    db.query(ConversationState).filter(ConversationState.user_id == uid).delete(synchronize_session="fetch")

    # Delete uploaded photos from disk
    uploads_dir = Path("uploads") / uid
    if uploads_dir.exists():
        rmtree(uploads_dir, ignore_errors=True)

    # Delete user (cascades to photos and profile via relationship)
    db.delete(current_user)
    db.commit()

    logger.info("Account permanently deleted: %s", email)
