import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.conversation import ConversationState
from app.models.match import Like, Match
from app.models.block import BlockedUser
from app.schemas.discover import DiscoverResponse
from app.services.matching_service import calculate_compatibility
from app.utils.profile_builder import build_discover_user

router = APIRouter()


def _calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _safe_date(year: int, month: int, day: int) -> date:
    """Handle Feb 29 → Feb 28 for non-leap years."""
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, month, day - 1)


@router.get("", response_model=DiscoverResponse)
def discover(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check onboarding status
    state = db.query(ConversationState).filter(ConversationState.user_id == current_user.id).first()
    if not state or state.onboarding_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete onboarding chat before discovering users",
        )

    # ── SQL-level filtering ──────────────────────────────────────────────
    q = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.photos))
        .filter(
            User.id != current_user.id,
            User.is_active == True,  # noqa: E712
        )
    )

    # Must have completed onboarding
    q = q.filter(User.id.in_(
        db.query(ConversationState.user_id)
        .filter(ConversationState.onboarding_status == "completed")
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

    # Location (exact-match, skip when either side is NULL)
    if current_user.location:
        q = q.filter(or_(User.location == None, User.location == current_user.location))  # noqa: E711

    # Bidirectional age-range
    if current_user.date_of_birth:
        my_age = _calculate_age(current_user.date_of_birth)
        today = date.today()

        # Candidate's DOB must put their age inside my [min, max]
        max_dob = _safe_date(today.year - current_user.age_range_min, today.month, today.day)
        min_dob_cutoff = _safe_date(today.year - current_user.age_range_max - 1, today.month, today.day)
        q = q.filter(or_(
            User.date_of_birth == None,  # noqa: E711
            and_(User.date_of_birth > min_dob_cutoff, User.date_of_birth <= max_dob),
        ))

        # My age must be inside candidate's [min, max]
        q = q.filter(User.age_range_min <= my_age, User.age_range_max >= my_age)

    candidates = q.all()

    # Deduplicate (joinedload on collections can produce duplicate rows)
    seen: set[str] = set()
    unique: list[User] = []
    for c in candidates:
        if c.id not in seen:
            seen.add(c.id)
            unique.append(c)

    # ── Python-level gender-preference filter (requires JSON parsing) ────
    user_gender_pref = json.loads(current_user.gender_preference) if current_user.gender_preference else None

    scored: list[tuple[User, float]] = []
    for c in unique:
        if user_gender_pref and c.gender and c.gender not in user_gender_pref:
            continue
        c_pref = json.loads(c.gender_preference) if c.gender_preference else None
        if c_pref and current_user.gender and current_user.gender not in c_pref:
            continue

        score = calculate_compatibility(current_user.profile, c.profile)
        scored.append((c, score))

    # Sort by compatibility and paginate
    scored.sort(key=lambda x: x[1], reverse=True)
    total = len(scored)
    page = scored[offset:offset + limit]

    users = [build_discover_user(c, s) for c, s in page]
    return DiscoverResponse(users=users, total=total, limit=limit, offset=offset)
