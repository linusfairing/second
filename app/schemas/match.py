from datetime import datetime
from pydantic import BaseModel

from app.schemas.discover import DiscoverUserResponse


class LikeRequest(BaseModel):
    liked_user_id: str


class LikeResponse(BaseModel):
    liked_user_id: str
    is_match: bool
    match_id: str | None = None


class PassRequest(BaseModel):
    passed_user_id: str


class PassResponse(BaseModel):
    passed_user_id: str


class MatchResponse(BaseModel):
    id: str
    other_user: DiscoverUserResponse
    compatibility_score: float | None = None
    created_at: datetime


class MatchListResponse(BaseModel):
    matches: list[MatchResponse]
    total: int
    limit: int
    offset: int
