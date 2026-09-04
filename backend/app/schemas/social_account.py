# backend/app/schemas/social_account.py — Social account schemas
# Cost classification: FREE + OPEN SOURCE

import uuid
from datetime import datetime
from pydantic import BaseModel

from app.models.social_account import Platform


class InstagramConnectResponse(BaseModel):
    authorization_url: str
    state: str


class SocialAccountResponse(BaseModel):
    id: uuid.UUID
    platform: Platform
    platform_user_id: str
    username: str
    token_expires_at: datetime | None
    scopes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InstagramCallbackResponse(BaseModel):
    social_account: SocialAccountResponse
