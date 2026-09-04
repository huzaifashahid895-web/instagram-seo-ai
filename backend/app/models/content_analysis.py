# backend/app/models/content_analysis.py — Content analysis (topic, duration, orientation, quality/hook/SEO scores, duplicate hash)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Float, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class ContentAnalysis(Base):
    __tablename__ = "content_analysis"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    # Topic & format
    topic: Mapped[str | None] = mapped_column(String(500), nullable=True)
    format: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., reel, carousel, post
    # Duration/orientation (for video)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    orientation: Mapped[str | None] = mapped_column(String(50), nullable=True)  # portrait, landscape, square
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Quality & hook scores (deterministic + LLM-scored)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    hook_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    seo_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    duplicate_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # SHA256 or imagehash
    # Relationships
    asset: Mapped["ContentAsset"] = relationship(back_populates="analysis")
