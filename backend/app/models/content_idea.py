# backend/app/models/content_idea.py — Content ideas (topic, format, rationale, predicted score)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    source_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True, index=True)
    # Idea content
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[str] = mapped_column(String(100), nullable=False)  # reel, carousel, post, story
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    predicted_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    # Status
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, approved, rejected, generated
    # Relationships
    source_asset: Mapped["ContentAsset"] = relationship(back_populates="content_ideas")
    generated_content: Mapped["GeneratedContent"] = relationship(back_populates="idea", uselist=False, cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)