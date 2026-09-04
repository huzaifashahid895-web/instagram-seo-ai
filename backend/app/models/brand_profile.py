# backend/app/models/brand_profile.py — Brand profile (niche, tone, audience, content pillars)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    # Core brand identity
    niche: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., fitness, travel, fashion
    tone: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., friendly, professional, playful
    audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_pillars: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    cta: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Call to action
    posting_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., 5 posts/week
    user: Mapped["User"] = relationship(back_populates="brand_profiles")
    # 1-1 relationship with social_account
    social_account: Mapped["SocialAccount"] = relationship(back_populates="brand_profile", uselist=False)
    # One-to-many: owns content assets
    content_assets: Mapped[list["ContentAsset"]] = relationship(back_populates="brand_profile", cascade="all, delete-orphan")
    # One-to-many: strategies
    content_strategies: Mapped[list["ContentStrategy"]] = relationship(back_populates="brand_profile", cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
