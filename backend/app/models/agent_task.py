# backend/app/models/agent_task.py — Agent task decision logs
# Cost classification: FREE + OPEN SOURCE

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class AgentTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    task_name: Mapped[str] = mapped_column(String(150), nullable=False)
    task_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON structured input
    output_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON structured output
    decision_log: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON structured decisions, no hidden chain-of-thought
    status: Mapped[AgentTaskStatus] = mapped_column(SQLEnum(AgentTaskStatus), default=AgentTaskStatus.PENDING, nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Relationships
    run: Mapped["AgentRun"] = relationship(back_populates="tasks")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
