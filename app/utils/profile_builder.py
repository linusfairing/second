import json

from app.models.user import User
from app.schemas.user import PhotoResponse, ProfileDataResponse, UserResponse
from app.schemas.discover import DiscoverUserResponse


def build_photos(user: User) -> list[PhotoResponse]:
    return [PhotoResponse.model_validate(p) for p in sorted(user.photos, key=lambda p: p.order_index)]


def build_profile_data(user: User) -> ProfileDataResponse | None:
    if not user.profile:
        return None
    p = user.profile
    return ProfileDataResponse(
        bio=p.bio,
        interests=json.loads(p.interests) if p.interests else None,
        values=json.loads(p.values) if p.values else None,
        personality_traits=json.loads(p.personality_traits) if p.personality_traits else None,
        relationship_goals=p.relationship_goals,
        communication_style=p.communication_style,
        profile_completeness=p.profile_completeness,
    )


def build_user_response(user: User) -> UserResponse:
    gender_pref = json.loads(user.gender_preference) if user.gender_preference else None
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        gender_preference=gender_pref,
        location=user.location,
        age_range_min=user.age_range_min,
        age_range_max=user.age_range_max,
        is_active=user.is_active,
        photos=build_photos(user),
        profile=build_profile_data(user),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def build_discover_user(user: User, score: float) -> DiscoverUserResponse:
    return DiscoverUserResponse(
        id=user.id,
        display_name=user.display_name,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        location=user.location,
        photos=build_photos(user),
        profile=build_profile_data(user),
        compatibility_score=round(score, 4),
        created_at=user.created_at,
    )
