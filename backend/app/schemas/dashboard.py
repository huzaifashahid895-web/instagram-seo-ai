# backend/app/schemas/dashboard.py — Dashboard response schemas
# Cost classification: FREE + OPEN SOURCE

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    social_accounts: int
    content_assets: int
    content_ideas: int
    generated_content: int
    posts: int
    scheduled_posts: int
    published_posts: int
    comments: int
    pending_approvals: int
    active_model_configs: int
