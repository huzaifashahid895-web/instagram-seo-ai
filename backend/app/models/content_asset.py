# backend/app/models/content_asset.py — Raw uploaded/library media
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class ContentAsset(Base):
    __tablename__ = "content_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)  # Storage path
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Content type hints
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # image, video, audio
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)  # seconds for video/audio
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 1-1 relationship with analysis
    analysis: Mapped["ContentAnalysis"] = relationship(back_populates="asset", uselist=False, cascade="all, delete-orphan")
    # One-to-many: ideas generated from this asset
    content_ideas: Mapped[list["ContentIdea"]] = relationship(back_populates="source_asset", cascade="all, delete-orphan")
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    brand_profile: Mapped["BrandProfile"] = relationship(back_populates="content_assets")
