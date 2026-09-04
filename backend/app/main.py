# backend/app/main.py — FastAPI application entry point
# Cost classification: FREE + OPEN SOURCE

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.db import init_db
from app.core.logging import setup_logging, get_logger
from app.api import (
    ai_studio, analytics, auth, comments, content, dashboard, 
    instagram, scheduler, seo, settings as settings_router, 
    social_accounts, webhooks, strategy, rag, agents, approvals
)

# Initialize structured logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting AI SEO & Social Media Manager backend")
    # Initialize database (creates tables if they don't exist)
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down backend")


app = FastAPI(
    title="AI SEO & Social Media Manager",
    description="Zero-cost, local-first Instagram content automation",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for local frontend dev (Vite on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Simple health check endpoint for Docker/load balancers."""
    return {"status": "ok"}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(social_accounts.router, prefix="/social-accounts", tags=["social-accounts"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(content.router, prefix="/content", tags=["content"])
app.include_router(ai_studio.router, prefix="/ai-studio", tags=["ai-studio"])
app.include_router(seo.router, prefix="/seo", tags=["seo"])
app.include_router(instagram.router, prefix="/instagram", tags=["instagram"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])
app.include_router(comments.router, prefix="/comments", tags=["comments"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
app.include_router(rag.router, prefix="/rag", tags=["rag"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])

logger.info("FastAPI app created")
# trigger reload 
