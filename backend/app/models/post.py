# backend/app/models/post.py — Posts (published or scheduled)
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base
from app.models.hashtag import post_hashtags
from app.models.keyword import post_keywords
import enum


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    generated_content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generated_content.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    # Platform-specific IDs
    platform_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Instagram media ID
    # Status & scheduling
    status: Mapped[PostStatus] = mapped_column(SQLEnum(PostStatus), default=PostStatus.DRAFT, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    # Caption & hashtags (denormalized for quick access)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags_text: Mapped[str | None] = mapped_column("hashtags", Text, nullable=True)  # JSON array
    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    # Relationships
    generated_content: Mapped["GeneratedContent"] = relationship(back_populates="post")
    social_account: Mapped["SocialAccount"] = relationship()
    variants: Mapped[list["PostVariant"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    caption_obj: Mapped["Caption"] = relationship(back_populates="post", uselist=False, cascade="all, delete-orphan")
    analytics: Mapped[list["Analytics"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    comments: Mapped[list["Comment"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    performance_rollups: Mapped[list["ContentPerformance"]] = relationship(back_populates="post")
    keywords: Mapped[list["Keyword"]] = relationship(secondary=post_keywords, back_populates="posts")
    hashtags: Mapped[list["Hashtag"]] = relationship(secondary=post_hashtags, back_populates="posts")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
