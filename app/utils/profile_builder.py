import json
import logging

from app.models.user import User
from app.schemas.user import PhotoResponse, ProfileDataResponse, UserResponse
from app.schemas.discover import DiscoverUserResponse

logger = logging.getLogger(__name__)


def _safe_json_loads(value: str | None, fallback=None):
    """Parse JSON string safely, returning fallback on error."""
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Malformed JSON in database field: %.100s", value)
        return fallback


def build_photos(user: User) -> list[PhotoResponse]:
    return [PhotoResponse.model_validate(p) for p in sorted(user.photos, key=lambda p: p.order_index)]


def build_profile_data(user: User) -> ProfileDataResponse | None:
    if not user.profile:
        return None
    p = user.profile
    return ProfileDataResponse(
        bio=p.bio,
        interests=_safe_json_loads(p.interests),
        values=_safe_json_loads(p.values),
        personality_traits=_safe_json_loads(p.personality_traits),
        relationship_goals=p.relationship_goals,
        communication_style=p.communication_style,
        profile_completeness=p.profile_completeness,
    )


def build_user_response(user: User) -> UserResponse:
    gender_pref = _safe_json_loads(user.gender_preference)
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
