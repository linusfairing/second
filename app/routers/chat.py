import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.profile import UserProfile
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessageResponse, ChatStatusResponse
from app.services.chat_service import process_message, get_conversation_history, get_or_create_state
from app.utils.rate_limiter import chat_rate_limiter

router = APIRouter()


@router.post("", response_model=ChatResponse)
def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat_rate_limiter.check(current_user.id)

    state = get_or_create_state(db, current_user.id)
    if state.onboarding_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed. Use your profile to make changes.",
        )

    reply = process_message(db, current_user.id, request.message)

    return ChatResponse(
        reply=reply,
        current_topic=state.current_topic,
        onboarding_status=state.onboarding_status,
    )


@router.get("/history", response_model=list[ChatMessageResponse])
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages = get_conversation_history(db, current_user.id)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.get("/status", response_model=ChatStatusResponse)
def get_chat_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    state = get_or_create_state(db, current_user.id)
    topics_completed = json.loads(state.topics_completed) if state.topics_completed else []

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    completeness = profile.profile_completeness if profile else 0.0

    return ChatStatusResponse(
        current_topic=state.current_topic,
        topics_completed=topics_completed,
        onboarding_status=state.onboarding_status,
        profile_completeness=completeness,
    )
