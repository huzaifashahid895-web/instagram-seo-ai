# backend/app/api/dashboard.py — Dashboard summary route
# Cost classification: FREE + OPEN SOURCE

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.approval_queue import ApprovalQueue, ApprovalStatus
from app.models.comment import Comment
from app.models.content_asset import ContentAsset
from app.models.content_idea import ContentIdea
from app.models.generated_content import GeneratedContent
from app.models.model_config import ModelConfig
from app.models.post import Post, PostStatus
from app.models.social_account import SocialAccount
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse


router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        social_accounts=_count(db, SocialAccount),
        content_assets=_count(db, ContentAsset),
        content_ideas=_count(db, ContentIdea),
        generated_content=_count(db, GeneratedContent),
        posts=_count(db, Post),
        scheduled_posts=_count_where(db, Post, Post.status == PostStatus.SCHEDULED),
        published_posts=_count_where(db, Post, Post.status == PostStatus.PUBLISHED),
        comments=_count(db, Comment),
        pending_approvals=_count_where(db, ApprovalQueue, ApprovalQueue.status == ApprovalStatus.PENDING),
        active_model_configs=_count_where(db, ModelConfig, ModelConfig.is_active.is_(True)),
    )


def _count(db: Session, model: type) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _count_where(db: Session, model: type, condition) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(condition)) or 0)
