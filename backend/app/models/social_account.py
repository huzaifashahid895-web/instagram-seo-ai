# backend/app/models/social_account.py — Social account (OAuth tokens, encrypted at rest)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base
import enum


class Platform(str, enum.Enum):
    INSTAGRAM = "instagram"
    # Future: TIKTOK, YOUTUBE, etc.


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Instagram user ID
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    # Encrypted at rest (encryption handled in service layer)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of scopes
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="social_accounts")
    brand_profile: Mapped["BrandProfile"] = relationship(back_populates="social_account", uselist=False)