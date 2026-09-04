# backend/app/models/post_variant.py — Post variants (A/B hooks/crops)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class PostVariant(Base):
    __tablename__ = "post_variants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    # Variant details
    variant_type: Mapped[str] = mapped_column(String(50), nullable=False)  # hook, crop, caption, thumbnail
    variant_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON with variant specifics
    # Performance tracking
    performance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_winner: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Relationships
    post: Mapped["Post"] = relationship(back_populates="variants")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)