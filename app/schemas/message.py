from datetime import datetime
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: str
    match_id: str
    sender_id: str
    content: str
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
