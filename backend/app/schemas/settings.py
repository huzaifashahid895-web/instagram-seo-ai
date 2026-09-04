# backend/app/schemas/settings.py — Settings and model config schemas
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.model_config import ModelCapability


class RuntimeSettingsResponse(BaseModel):
    database_url: str
    chroma_host: str
    chroma_port: int
    log_level: str
    cors_origins: list[str]
    jwt_configured: bool
    encryption_configured: bool
    instagram_app_configured: bool
    instagram_redirect_uri: str


class ModelConfigCreate(BaseModel):
    capability: ModelCapability
    provider_name: str = Field(min_length=1, max_length=100)
    model_name: str = Field(min_length=1, max_length=255)
    endpoint_url: str | None = Field(default=None, max_length=512)
    parameters: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    is_active: bool = True
    is_local: bool = True


class ModelConfigUpdate(BaseModel):
    provider_name: str | None = Field(default=None, min_length=1, max_length=100)
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    endpoint_url: str | None = Field(default=None, max_length=512)
    parameters: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    is_local: bool | None = None


class ModelConfigResponse(BaseModel):
    id: uuid.UUID
    capability: ModelCapability
    provider_name: str
    model_name: str
    endpoint_url: str | None
    parameters: str | None
    temperature: float | None
    max_tokens: int | None
    is_active: bool
    is_local: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
