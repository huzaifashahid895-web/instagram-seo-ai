# backend/app/models/model_config.py — Provider configuration
# Cost classification: FREE + OPEN SOURCE

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Enum as SQLEnum, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class ModelCapability(str, enum.Enum):
    LLM = "llm"
    EMBEDDINGS = "embeddings"
    STT = "stt"
    TTS = "tts"
    VISION = "vision"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    capability: Mapped[ModelCapability] = mapped_column(SQLEnum(ModelCapability), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON provider/model parameters
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_local: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
