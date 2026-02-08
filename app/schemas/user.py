from datetime import date, datetime
from pydantic import BaseModel, model_validator


class UserUpdate(BaseModel):
    display_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    gender_preference: list[str] | None = None
    location: str | None = None
    age_range_min: int | None = None
    age_range_max: int | None = None

    @model_validator(mode="after")
    def check_age_range(self):
        if self.age_range_min is not None and self.age_range_max is not None:
            if self.age_range_min > self.age_range_max:
                raise ValueError("age_range_min must not exceed age_range_max")
        return self


class ProfileUpdate(BaseModel):
    bio: str | None = None
    interests: list[str] | None = None
    values: list[str] | None = None
    personality_traits: list[str] | None = None
    relationship_goals: str | None = None
    communication_style: str | None = None


class PhotoResponse(BaseModel):
    id: str
    file_path: str
    is_primary: bool
    order_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileDataResponse(BaseModel):
    bio: str | None = None
    interests: list | None = None
    values: list | None = None
    personality_traits: list | None = None
    relationship_goals: str | None = None
    communication_style: str | None = None
    profile_completeness: float = 0.0


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    gender_preference: list[str] | None = None
    location: str | None = None
    age_range_min: int = 18
    age_range_max: int = 99
    is_active: bool = True
    photos: list[PhotoResponse] = []
    profile: ProfileDataResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
