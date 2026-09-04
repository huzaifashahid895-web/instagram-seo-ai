# backend/app/models/keyword.py — Keywords (N—N with posts via join table)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Float, Integer, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


# Association table for posts <-> keywords (many-to-many)
post_keywords = Table(
    "post_keywords",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("keyword_id", ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
)


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Keyword data
    term: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    cluster: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Semantic cluster
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    frequency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Relationships
    posts: Mapped[list["Post"]] = relationship(secondary=post_keywords, back_populates="keywords")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)