# backend/app/models/caption.py — Captions (per post)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class Caption(Base):
    __tablename__ = "captions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    # Caption content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Metadata
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    # Relationships
    post: Mapped["Post"] = relationship(back_populates="caption_obj")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
