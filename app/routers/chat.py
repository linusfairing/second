import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.profile import UserProfile
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessageResponse, ChatStatusResponse
from app.services.chat_service import process_message, get_conversation_history, get_or_create_state

from app.utils.rate_limiter import chat_rate_limiter

router = APIRouter()

ONBOARDING_COMPLETED = "completed"
ONBOARDING_IN_PROGRESS = "in_progress"


@router.post("", response_model=ChatResponse)
def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.profile_setup_complete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete your profile setup first",
        )

    chat_rate_limiter.check(current_user.id)

    state = get_or_create_state(db, current_user.id)
    if state.onboarding_status == ONBOARDING_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed. Use your profile to make changes.",
        )

    reply = process_message(db, current_user.id, request.message, state=state)

    return ChatResponse(
        reply=reply,
        current_topic=state.current_topic,
        onboarding_status=state.onboarding_status,
    )


@router.get("/intro")
def get_chat_intro(
    current_user: User = Depends(get_current_user),
):
    name = (current_user.display_name or "there").split()[0]
    return {
        "messages": [
            "Hey, I'm Mutual. Just so you know \u2014 I'm an AI, not a real person. I'm here to get to know the real you, not the dating profile version. Everything here stays between us unless you choose otherwise. No wrong answers, and the more real you are with me, the easier it is for me to find someone you'll click with.",
            f"So {name}, tell me some things you like. Literally anything \u2014 hobbies, TV shows, food, places, something weird, doesn't matter. Just whatever comes to mind.",
        ]
    }


@router.get("/history", response_model=list[ChatMessageResponse])
def get_chat_history(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages = get_conversation_history(db, current_user.id, limit=limit, offset=offset)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.get("/status", response_model=ChatStatusResponse)
def get_chat_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    state = get_or_create_state(db, current_user.id)
    try:
        topics_completed = json.loads(state.topics_completed) if state.topics_completed else []
    except (json.JSONDecodeError, TypeError):
        topics_completed = []

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    completeness = profile.profile_completeness if profile else 0.0

    return ChatStatusResponse(
        current_topic=state.current_topic,
        topics_completed=topics_completed,
        onboarding_status=state.onboarding_status,
        profile_completeness=completeness,
        profile_setup_complete=bool(current_user.profile_setup_complete),
    )
