from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.block import BlockedUser
from app.services.auth_service import decode_access_token

security = HTTPBearer()

ACTIVE_EXEMPT_PATHS = {"/api/v1/account/reactivate", "/api/v1/account/status", "/api/v1/account"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Check if token was issued before a forced invalidation
    iat = payload.get("iat")
    if iat is not None and user.token_invalidated_at is not None:
        from datetime import datetime, timezone
        inv = user.token_invalidated_at
        invalidated_ts = inv.timestamp() if inv.tzinfo else inv.replace(tzinfo=timezone.utc).timestamp()
        if iat <= invalidated_ts:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    if not user.is_active and request.url.path not in ACTIVE_EXEMPT_PATHS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    return user


def check_block(db: Session, user1_id: str, user2_id: str, detail: str = "Cannot interact with blocked user") -> None:
    """Raise 403 if a block exists in either direction between the two users."""
    block = db.query(BlockedUser).filter(
        ((BlockedUser.blocker_id == user1_id) & (BlockedUser.blocked_id == user2_id))
        | ((BlockedUser.blocker_id == user2_id) & (BlockedUser.blocked_id == user1_id))
    ).first()
    if block:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
