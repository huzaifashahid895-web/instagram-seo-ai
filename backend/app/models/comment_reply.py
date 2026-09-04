# backend/app/models/comment_reply.py — Comment replies
# Cost classification: FREE + OPEN SOURCE

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class CommentReplyStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"


class CommentReply(Base):
    __tablename__ = "comment_replies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Platform data
    platform_reply_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    reply_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON payload from platform
    # Workflow state
    status: Mapped[CommentReplyStatus] = mapped_column(SQLEnum(CommentReplyStatus), default=CommentReplyStatus.DRAFT, nullable=False, index=True)
    generated_by_agent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Relationships
    comment: Mapped["Comment"] = relationship(back_populates="replies")
    approved_by: Mapped["User | None"] = relationship()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
