from datetime import date, datetime
from pydantic import BaseModel, Field, model_validator


HIDEABLE_FIELDS = frozenset({
    "home_town", "gender", "sexual_orientation", "job_title",
    "college_university", "languages", "ethnicity", "religion", "children",
    "family_plans", "drinking", "smoking", "marijuana", "drugs",
    "relationship_goals",
})


class ProfileSetupRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    height_inches: int = Field(..., ge=48, le=84)
    location: str = Field(..., min_length=1, max_length=100)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    max_distance_km: int = Field(50, ge=1, le=500)
    home_town: str = Field(..., min_length=1, max_length=200)
    gender: str = Field(..., min_length=1, max_length=30)
    sexual_orientation: str = Field(..., min_length=1, max_length=100)
    job_title: str = Field(..., min_length=1, max_length=200)
    college_university: str = Field(..., min_length=1, max_length=200)
    education_level: str = Field(..., min_length=1, max_length=100)
    languages: list[str] = Field(..., min_length=1, max_length=20)
    ethnicity: str = Field(..., min_length=1, max_length=100)
    religion: str = Field(..., min_length=1, max_length=100)
    children: str = Field(..., min_length=1, max_length=100)
    family_plans: str = Field(..., min_length=1, max_length=100)
    drinking: str = Field(..., min_length=1, max_length=50)
    smoking: str = Field(..., min_length=1, max_length=50)
    marijuana: str = Field(..., min_length=1, max_length=50)
    drugs: str = Field(..., min_length=1, max_length=50)
    relationship_goals: str = Field(..., min_length=1, max_length=100)
    hidden_fields: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_hidden_fields(self):
        invalid = set(self.hidden_fields) - HIDEABLE_FIELDS
        if invalid:
            raise ValueError(f"Invalid hidden_fields: {sorted(invalid)}. Allowed: {sorted(HIDEABLE_FIELDS)}")
        return self


class UserUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(None, max_length=30)
    gender_preference: list[str] | None = Field(None, max_length=10)
    location: str | None = Field(None, max_length=100)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    max_distance_km: int | None = Field(None, ge=1, le=500)
    age_range_min: int | None = Field(None, ge=18, le=120)
    age_range_max: int | None = Field(None, ge=18, le=120)
    height_inches: int | None = Field(None, ge=48, le=84)
    home_town: str | None = Field(None, max_length=200)
    sexual_orientation: str | None = Field(None, max_length=100)
    job_title: str | None = Field(None, max_length=200)
    college_university: str | None = Field(None, max_length=200)
    education_level: str | None = Field(None, max_length=100)
    languages: list[str] | None = Field(None, max_length=20)
    ethnicity: str | None = Field(None, max_length=100)
    religion: str | None = Field(None, max_length=100)
    children: str | None = Field(None, max_length=100)
    family_plans: str | None = Field(None, max_length=100)
    drinking: str | None = Field(None, max_length=50)
    smoking: str | None = Field(None, max_length=50)
    marijuana: str | None = Field(None, max_length=50)
    drugs: str | None = Field(None, max_length=50)
    relationship_goals: str | None = Field(None, max_length=100)
    hidden_fields: list[str] | None = Field(None, max_length=20)

    @model_validator(mode="after")
    def check_age_range(self):
        if self.age_range_min is not None and self.age_range_max is not None:
            if self.age_range_min > self.age_range_max:
                raise ValueError("age_range_min must not exceed age_range_max")
        return self

    @model_validator(mode="after")
    def validate_hidden_fields(self):
        if self.hidden_fields is not None:
            invalid = set(self.hidden_fields) - HIDEABLE_FIELDS
            if invalid:
                raise ValueError(f"Invalid hidden_fields: {sorted(invalid)}. Allowed: {sorted(HIDEABLE_FIELDS)}")
        return self


class ProfileUpdate(BaseModel):
    bio: str | None = Field(None, max_length=2000)
    interests: list[str] | None = Field(None, max_length=50)
    values: list[str] | None = Field(None, max_length=50)
    personality_traits: list[str] | None = Field(None, max_length=50)
    relationship_goals: str | None = Field(None, max_length=200)
    communication_style: str | None = Field(None, max_length=200)


class PhotoResponse(BaseModel):
    id: str
    file_path: str
    is_primary: bool
    order_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileDataResponse(BaseModel):
    bio: str | None = None
    interests: list[str] | None = None
    values: list[str] | None = None
    personality_traits: list[str] | None = None
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
    latitude: float | None = None
    longitude: float | None = None
    max_distance_km: int = 50
    age_range_min: int = 18
    age_range_max: int = 99
    height_inches: int | None = None
    home_town: str | None = None
    sexual_orientation: str | None = None
    job_title: str | None = None
    college_university: str | None = None
    education_level: str | None = None
    languages: list[str] | None = None
    ethnicity: str | None = None
    religion: str | None = None
    children: str | None = None
    family_plans: str | None = None
    drinking: str | None = None
    smoking: str | None = None
    marijuana: str | None = None
    drugs: str | None = None
    relationship_goals: str | None = None
    hidden_fields: list[str] | None = None
    profile_setup_complete: bool = False
    is_active: bool = True
    photos: list[PhotoResponse] = []
    profile: ProfileDataResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
