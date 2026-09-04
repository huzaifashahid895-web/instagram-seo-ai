# backend/app/models/generated_content.py — Generated content (script, media refs, voice, subtitles)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class GeneratedContent(Base):
    __tablename__ = "generated_content"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    idea_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_ideas.id", ondelete="CASCADE"), nullable=False, index=True)
    # Generated content
    script: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_refs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list of paths/URLs
    voice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # TTS voice identifier
    subtitles: Mapped[str | None] = mapped_column(Text, nullable=True)  # SRT/VTT content
    # Quality scores
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    seo_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Status
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, approved, rejected, published
    # Relationships
    idea: Mapped["ContentIdea"] = relationship(back_populates="generated_content")
    post: Mapped["Post"] = relationship(back_populates="generated_content", uselist=False, cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)