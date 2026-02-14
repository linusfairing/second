import json
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User, UserPhoto
from app.models.profile import UserProfile
from app.schemas.user import ProfileSetupRequest, UserUpdate, ProfileUpdate, UserResponse, PhotoResponse, ProfileDataResponse
from app.utils.profile_builder import build_user_response, build_profile_data

router = APIRouter()

MAX_PHOTOS = 6
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return build_user_response(current_user)


@router.post("/me/setup", response_model=UserResponse)
def setup_profile(
    data: ProfileSetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate age >= 18
    today = date.today()
    age = today.year - data.date_of_birth.year - (
        (today.month, today.day) < (data.date_of_birth.month, data.date_of_birth.day)
    )
    if age < 18:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Must be at least 18 years old",
        )

    # Require at least 3 photos
    photo_count = db.query(UserPhoto).filter(UserPhoto.user_id == current_user.id).count()
    if photo_count < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least 3 photos required (you have {photo_count})",
        )

    current_user.display_name = data.display_name
    current_user.date_of_birth = data.date_of_birth
    current_user.height_inches = data.height_inches
    current_user.location = data.location
    current_user.home_town = data.home_town
    current_user.gender = data.gender
    current_user.sexual_orientation = data.sexual_orientation
    current_user.job_title = data.job_title
    current_user.college_university = data.college_university
    current_user.education_level = data.education_level
    current_user.languages = json.dumps(data.languages)
    current_user.ethnicity = data.ethnicity
    current_user.religion = data.religion
    current_user.children = data.children
    current_user.family_plans = data.family_plans
    current_user.drinking = data.drinking
    current_user.smoking = data.smoking
    current_user.marijuana = data.marijuana
    current_user.drugs = data.drugs
    current_user.hidden_fields = json.dumps(data.hidden_fields)
    current_user.profile_setup_complete = True

    db.commit()
    db.refresh(current_user)
    return build_user_response(current_user)


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if update.display_name is not None:
        current_user.display_name = update.display_name
    if update.date_of_birth is not None:
        today = date.today()
        age = today.year - update.date_of_birth.year - (
            (today.month, today.day) < (update.date_of_birth.month, update.date_of_birth.day)
        )
        if age < 18:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Must be at least 18 years old",
            )
        current_user.date_of_birth = update.date_of_birth
    if update.gender is not None:
        current_user.gender = update.gender
    if update.gender_preference is not None:
        current_user.gender_preference = json.dumps(update.gender_preference)
    if update.location is not None:
        current_user.location = update.location
    if update.age_range_min is not None:
        current_user.age_range_min = update.age_range_min
    if update.age_range_max is not None:
        current_user.age_range_max = update.age_range_max
    if update.height_inches is not None:
        current_user.height_inches = update.height_inches
    if update.home_town is not None:
        current_user.home_town = update.home_town
    if update.sexual_orientation is not None:
        current_user.sexual_orientation = update.sexual_orientation
    if update.job_title is not None:
        current_user.job_title = update.job_title
    if update.college_university is not None:
        current_user.college_university = update.college_university
    if update.education_level is not None:
        current_user.education_level = update.education_level
    if update.languages is not None:
        current_user.languages = json.dumps(update.languages)
    if update.ethnicity is not None:
        current_user.ethnicity = update.ethnicity
    if update.religion is not None:
        current_user.religion = update.religion
    if update.children is not None:
        current_user.children = update.children
    if update.family_plans is not None:
        current_user.family_plans = update.family_plans
    if update.drinking is not None:
        current_user.drinking = update.drinking
    if update.smoking is not None:
        current_user.smoking = update.smoking
    if update.marijuana is not None:
        current_user.marijuana = update.marijuana
    if update.drugs is not None:
        current_user.drugs = update.drugs
    if update.hidden_fields is not None:
        current_user.hidden_fields = json.dumps(update.hidden_fields)

    if current_user.age_range_min > current_user.age_range_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="age_range_min must not exceed age_range_max",
        )

    db.commit()
    db.refresh(current_user)
    return build_user_response(current_user)


@router.put("/me/profile", response_model=ProfileDataResponse)
def update_my_profile_details(
    update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    if update.bio is not None:
        profile.bio = update.bio
    if update.interests is not None:
        profile.interests = json.dumps(update.interests)
    if update.values is not None:
        profile.values = json.dumps(update.values)
    if update.personality_traits is not None:
        profile.personality_traits = json.dumps(update.personality_traits)
    if update.relationship_goals is not None:
        profile.relationship_goals = update.relationship_goals
    if update.communication_style is not None:
        profile.communication_style = update.communication_style

    # Recalculate completeness (must match chat_service._apply_profile_updates)
    fields = ["bio", "interests", "values", "personality_traits", "relationship_goals",
              "communication_style", "deal_breakers", "life_goals", "dating_style", "conversation_highlights"]
    filled = sum(1 for f in fields if getattr(profile, f, None) is not None)
    profile.profile_completeness = filled / len(fields)

    db.commit()
    db.refresh(profile)
    # Refresh the user relationship so build_profile_data sees the updated profile
    db.refresh(current_user)
    return build_profile_data(current_user)


@router.post("/me/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    photo_count = db.query(UserPhoto).filter(UserPhoto.user_id == current_user.id).count()
    if photo_count >= MAX_PHOTOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum {MAX_PHOTOS} photos allowed")

    # Validate content type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

    # Validate extension
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

    # Read in chunks and enforce size limit early
    chunks = []
    bytes_read = 0
    while True:
        chunk = file.file.read(1024 * 1024)  # 1 MB chunks
        if not chunk:
            break
        bytes_read += len(chunk)
        if bytes_read > MAX_PHOTO_SIZE:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 5 MB limit")
        chunks.append(chunk)
    content = b"".join(chunks)

    # Verify actual image content via magic bytes
    IMAGE_SIGNATURES = {
        b"\xff\xd8\xff": ".jpg",       # JPEG
        b"\x89PNG\r\n\x1a\n": ".png",  # PNG
        b"GIF87a": ".gif",             # GIF87a
        b"GIF89a": ".gif",             # GIF89a
    }
    is_valid_image = any(content.startswith(sig) for sig in IMAGE_SIGNATURES)
    # WebP: RIFF container with WEBP chunk at offset 8
    if not is_valid_image and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        is_valid_image = True
    if not is_valid_image:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File content is not a valid image")

    # Sanitize filename
    filename = f"{uuid.uuid4().hex}{ext}"
    user_dir = Path("uploads") / current_user.id
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / filename

    file_path.write_bytes(content)

    relative_path = f"{current_user.id}/{filename}"
    is_primary = photo_count == 0

    max_index = db.query(func.max(UserPhoto.order_index)).filter(
        UserPhoto.user_id == current_user.id
    ).scalar()
    next_index = (max_index + 1) if max_index is not None else 0

    photo = UserPhoto(
        user_id=current_user.id,
        file_path=relative_path,
        is_primary=is_primary,
        order_index=next_index,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return PhotoResponse.model_validate(photo)


@router.delete("/me/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    photo = db.query(UserPhoto).filter(
        UserPhoto.id == photo_id, UserPhoto.user_id == current_user.id
    ).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    was_primary = photo.is_primary

    uploads_root = Path("uploads").resolve()
    file_path = (uploads_root / photo.file_path).resolve()
    if file_path.is_relative_to(uploads_root) and file_path.exists():
        file_path.unlink()

    db.delete(photo)

    # Promote next photo to primary if we just deleted the primary
    if was_primary:
        next_photo = (
            db.query(UserPhoto)
            .filter(UserPhoto.user_id == current_user.id, UserPhoto.id != photo_id)
            .order_by(UserPhoto.order_index)
            .first()
        )
        if next_photo:
            next_photo.is_primary = True

    db.commit()
