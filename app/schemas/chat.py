from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    current_topic: str
    onboarding_status: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    topic: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatStatusResponse(BaseModel):
    current_topic: str
    topics_completed: list[str]
    onboarding_status: str
    profile_completeness: float
    profile_setup_complete: bool = False
    dating_preferences_complete: bool = False
