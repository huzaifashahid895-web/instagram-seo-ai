# backend/app/api/__init__.py — API router package
# Cost classification: FREE + OPEN SOURCE

from app.api.auth import router as auth_router
from app.api.social_accounts import router as social_accounts_router
from app.api.settings import router as settings_router
from app.api.content import router as content_router
from app.api.dashboard import router as dashboard_router
from app.api.scheduler import router as scheduler_router
from app.api.comments import router as comments_router
from app.api.analytics import router as analytics_router
from app.api.ai_studio import router as ai_studio_router
from app.api.seo import router as seo_router
from app.api.instagram import router as instagram_router
from app.api.webhooks import router as webhooks_router
from app.api.strategy import router as strategy_router
from app.api.rag import router as rag_router
from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router

__all__ = [
    "auth_router",
    "social_accounts_router",
    "settings_router",
    "content_router",
    "dashboard_router",
    "scheduler_router",
    "comments_router",
    "analytics_router",
    "ai_studio_router",
    "seo_router",
    "instagram_router",
    "webhooks_router",
    "strategy_router",
    "rag_router",
    "agents_router",
    "approvals_router",
]
