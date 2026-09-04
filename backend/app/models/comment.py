# backend/app/models/comment.py — Comments (per post)
# Cost classification: FREE + OPEN SOURCE

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class CommentClassification(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    QUESTION = "question"
    PRODUCT_QUESTION = "product_question"
    SUPPORT = "support"
    COMPLAINT = "complaint"
    SPAM = "spam"
    TROLL = "troll"
    OFF_TOPIC = "off_topic"
    PRAISE = "praise"
    REQUEST = "request"
    SENSITIVE = "sensitive"
    UNKNOWN = "unknown"


class CommentSentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class CommentStatus(str, enum.Enum):
    NEW = "new"
    REVIEWING = "reviewing"
    REPLIED = "replied"
    HIDDEN = "hidden"
    IGNORED = "ignored"
    ESCALATED = "escalated"


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    # Platform data
    platform_comment_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    author_platform_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON payload from platform
    # Classification and moderation
    classification: Mapped[CommentClassification] = mapped_column(SQLEnum(CommentClassification), default=CommentClassification.UNKNOWN, nullable=False)
    sentiment: Mapped[CommentSentiment] = mapped_column(SQLEnum(CommentSentiment), default=CommentSentiment.UNKNOWN, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[CommentStatus] = mapped_column(SQLEnum(CommentStatus), default=CommentStatus.NEW, nullable=False, index=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # Relationships
    post: Mapped["Post"] = relationship(back_populates="comments")
    replies: Mapped[list["CommentReply"]] = relationship(back_populates="comment", cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
