# backend/app/models/hashtag.py — Hashtags (N—N with posts)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Float, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


# Association table for posts <-> hashtags (many-to-many)
post_hashtags = Table(
    "post_hashtags",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("hashtag_id", ForeignKey("hashtags.id", ondelete="CASCADE"), primary_key=True),
)


class Hashtag(Base):
    __tablename__ = "hashtags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Hashtag data
    tag: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    historical_performance: Mapped[float | None] = mapped_column(Float, nullable=True)  # avg engagement
    # Relationships
    posts: Mapped[list["Post"]] = relationship(secondary=post_hashtags, back_populates="hashtags")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)