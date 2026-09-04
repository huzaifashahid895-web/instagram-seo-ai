# backend/app/models/content_strategy.py — Content strategy snapshots
# Cost classification: FREE + OPEN SOURCE

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class ContentStrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ContentStrategy(Base):
    __tablename__ = "content_strategies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    # Strategy snapshot
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    niche_focus: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_pillars: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    posting_plan: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON schedule/frequency plan
    seo_focus_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    avoid_topics: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    predicted_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[ContentStrategyStatus] = mapped_column(SQLEnum(ContentStrategyStatus), default=ContentStrategyStatus.DRAFT, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Relationships
    brand_profile: Mapped["BrandProfile"] = relationship(back_populates="content_strategies")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
