from datetime import date, datetime
from pydantic import BaseModel

from app.schemas.user import PhotoResponse, ProfileDataResponse


class DiscoverUserResponse(BaseModel):
    id: str
    display_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    location: str | None = None
    photos: list[PhotoResponse] = []
    profile: ProfileDataResponse | None = None
    compatibility_score: float = 0.0
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoverResponse(BaseModel):
    users: list[DiscoverUserResponse]
    total: int
    limit: int
    offset: int
