import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
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
