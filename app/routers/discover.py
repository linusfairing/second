import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session, subqueryload

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.conversation import ConversationState
from app.models.match import Like, Match
from app.models.block import BlockedUser
from app.schemas.discover import DiscoverResponse
from app.services.matching_service import calculate_compatibility
from app.services.chat_service import ONBOARDING_COMPLETED
from app.utils.profile_builder import build_discover_user, _safe_json_loads, haversine_km

router = APIRouter()


def _calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _safe_date(year: int, month: int, day: int) -> date:
    """Handle Feb 29 → Feb 28 for non-leap years, and edge cases like day=1."""
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, max_day))


@router.get("", response_model=DiscoverResponse)
def discover(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check onboarding status
    state = db.query(ConversationState).filter(ConversationState.user_id == current_user.id).first()
    if not state or state.onboarding_status != ONBOARDING_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete onboarding chat before discovering users",
        )

    # ── SQL-level filtering ──────────────────────────────────────────────
    q = (
        db.query(User)
        .options(subqueryload(User.profile), subqueryload(User.photos))
        .filter(
            User.id != current_user.id,
            User.is_active == True,  # noqa: E712
            User.profile_setup_complete == True,  # noqa: E712
        )
    )

    # Must have completed onboarding
    q = q.filter(User.id.in_(
        db.query(ConversationState.user_id)
        .filter(ConversationState.onboarding_status == ONBOARDING_COMPLETED)
    ))

    # Exclude liked / passed
    q = q.filter(~User.id.in_(
        db.query(Like.liked_id).filter(Like.liker_id == current_user.id)
    ))

    # Exclude matched (both FK columns)
    q = q.filter(
        ~User.id.in_(db.query(Match.user2_id).filter(Match.user1_id == current_user.id)),
        ~User.id.in_(db.query(Match.user1_id).filter(Match.user2_id == current_user.id)),
    )

    # Exclude blocked (both directions)
    q = q.filter(
        ~User.id.in_(db.query(BlockedUser.blocked_id).filter(BlockedUser.blocker_id == current_user.id)),
        ~User.id.in_(db.query(BlockedUser.blocker_id).filter(BlockedUser.blocked_id == current_user.id)),
    )

    # Rough bounding-box pre-filter for distance (if current user has GPS)
    if current_user.latitude is not None and current_user.longitude is not None:
        max_km = current_user.max_distance_km or 50
        lat_delta = max_km / 111.0
        cos_lat = math.cos(math.radians(current_user.latitude))
        lon_delta = max_km / (111.0 * max(cos_lat, 0.01))
        q = q.filter(or_(
            User.latitude.is_(None),
            and_(
                User.latitude >= current_user.latitude - lat_delta,
                User.latitude <= current_user.latitude + lat_delta,
                User.longitude >= current_user.longitude - lon_delta,
                User.longitude <= current_user.longitude + lon_delta,
            ),
        ))

    # Bidirectional age-range
    if current_user.date_of_birth:
        my_age = _calculate_age(current_user.date_of_birth)
        today = date.today()

        # Candidate's DOB must put their age inside my [min, max]
        max_dob = _safe_date(today.year - current_user.age_range_min, today.month, today.day)
        min_dob_cutoff = _safe_date(today.year - current_user.age_range_max - 1, today.month, today.day)
        q = q.filter(or_(
            User.date_of_birth.is_(None),
            and_(User.date_of_birth > min_dob_cutoff, User.date_of_birth <= max_dob),
        ))

        # My age must be inside candidate's [min, max]
        q = q.filter(User.age_range_min <= my_age, User.age_range_max >= my_age)

    # Deterministic ordering + SQL-level limit to avoid loading the entire table.
    # Over-fetch to account for Python-level gender + distance filtering below.
    sql_limit = (offset + limit) * 4 + 50
    candidates = q.order_by(User.created_at.desc()).limit(sql_limit).all()

    # ── Python-level gender-preference filter (requires JSON parsing) ────
    user_gender_pref = _safe_json_loads(current_user.gender_preference)

    has_gps = (current_user.latitude is not None and current_user.longitude is not None)

    scored: list[tuple[User, float, float | None]] = []
    for c in candidates:
        if user_gender_pref and c.gender and c.gender not in user_gender_pref:
            continue
        c_pref = _safe_json_loads(c.gender_preference)
        if c_pref and current_user.gender and current_user.gender not in c_pref:
            continue

        # Distance filtering (precise haversine after SQL bounding-box)
        distance = None
        if has_gps and c.latitude is not None and c.longitude is not None:
            distance = haversine_km(
                current_user.latitude, current_user.longitude,
                c.latitude, c.longitude,
            )
            max_km = current_user.max_distance_km or 50
            if distance > max_km:
                continue

        score = calculate_compatibility(current_user.profile, c.profile)
        scored.append((c, score, distance))

    # Sort by compatibility and paginate
    scored.sort(key=lambda x: x[1], reverse=True)
    total = len(scored)
    page = scored[offset:offset + limit]

    users = [build_discover_user(c, s, d) for c, s, d in page]
    return DiscoverResponse(users=users, total=total, limit=limit, offset=offset)
