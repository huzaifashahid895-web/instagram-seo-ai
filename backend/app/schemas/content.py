# backend/app/schemas/content.py — Content library schemas
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from pydantic import BaseModel


class ContentAssetResponse(BaseModel):
    id: uuid.UUID
    brand_profile_id: uuid.UUID
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    media_type: str
    duration: float | None
    width: int | None
    height: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentAnalysisResponse(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    topic: str | None
    format: str | None
    duration: float | None
    orientation: str | None
    file_size: int | None
    width: int | None
    height: int | None
    quality_score: float | None
    hook_score: float | None
    seo_score: float | None
    duplicate_hash: str | None

    model_config = {"from_attributes": True}
