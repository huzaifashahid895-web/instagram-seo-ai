# backend/app/models/rag_document.py — RAG source documents
# Cost classification: FREE + OPEN SOURCE

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class RagSourceType(str, enum.Enum):
    BRAND_PROFILE = "brand_profile"
    CONTENT_ASSET = "content_asset"
    POST = "post"
    COMMENT = "comment"
    STRATEGY = "strategy"
    NOTE = "note"
    EXTERNAL = "external"


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    source_type: Mapped[RagSourceType] = mapped_column(SQLEnum(RagSourceType), nullable=False, index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    document_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON metadata
    # Relationships
    brand_profile: Mapped["BrandProfile | None"] = relationship()
    chunks: Mapped[list["RagChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
