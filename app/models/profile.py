import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    interests: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    values: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    personality_traits: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON dict/array
    relationship_goals: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    communication_style: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    deal_breakers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    life_goals: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    dating_style: Mapped[str | None] = mapped_column(Text, nullable=True)  # string description
    conversation_highlights: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of quotes/stories
    profile_completeness: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="profile")


from app.models.user import User  # noqa: E402, F401
