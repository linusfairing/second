import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.user import User
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.utils.rate_limiter import auth_rate_limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    auth_rate_limiter.check(request.email.lower())
    email = request.email.lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Registration failed")

    user = User(
        email=email,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("New user signup: %s", user.email)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_id=user.id, is_active=user.is_active)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    auth_rate_limiter.check(request.email.lower())
    user = db.query(User).filter(User.email == request.email.lower()).first()
    if not user:
        # Run hash anyway to prevent timing-based user enumeration
        hash_password("dummy-password")
        logger.warning("Failed login attempt for email: %s", request.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not verify_password(request.password, user.hashed_password):
        logger.warning("Failed login attempt for email: %s", request.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    logger.info("User login: %s (active=%s)", user.email, user.is_active)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_id=user.id, is_active=user.is_active)
