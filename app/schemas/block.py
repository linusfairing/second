from datetime import datetime
from pydantic import BaseModel


class BlockRequest(BaseModel):
    blocked_user_id: str


class BlockResponse(BaseModel):
    blocked_user_id: str
    auto_unmatched: bool = False


class BlockedUserResponse(BaseModel):
    id: str
    blocked_user_id: str
    created_at: datetime


class BlockedUserListResponse(BaseModel):
    blocks: list[BlockedUserResponse]
    total: int
    limit: int
    offset: int
