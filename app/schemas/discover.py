from datetime import date, datetime
from pydantic import BaseModel

from app.schemas.user import PhotoResponse, ProfileDataResponse


class DiscoverUserResponse(BaseModel):
    id: str
    display_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    location: str | None = None
    height_inches: int | None = None
    home_town: str | None = None
    sexual_orientation: str | None = None
    job_title: str | None = None
    college_university: str | None = None
    languages: list[str] | None = None
    ethnicity: str | None = None
    religion: str | None = None
    children: str | None = None
    family_plans: str | None = None
    drinking: str | None = None
    smoking: str | None = None
    marijuana: str | None = None
    drugs: str | None = None
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
