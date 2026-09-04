# backend/app/schemas/comments.py — Comment schemas
# Cost classification: FREE + OPEN SOURCE

"""
Pydantic schemas for comment management API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models import (
    CommentClassification, CommentSentiment, CommentStatus,
    CommentReplyStatus
)


class CommentBase(BaseModel):
    """Base comment schema."""
    post_id: str = Field(..., description="Platform post ID")
    platform_comment_id: str = Field(..., description="Platform comment ID")
    author_platform_id: Optional[str] = Field(None, description="Platform author ID")
    author_username: Optional[str] = Field(None, description="Author username")
    text: str = Field(..., min_length=1, max_length=1000, description="Comment text")
    raw_payload: Optional[str] = Field(None, description="Raw JSON payload from platform")


class CommentCreate(CommentBase):
    """Schema for creating a new comment."""
    pass


class CommentResponse(CommentBase):
    """Schema for comment response."""
    id: str
    classification: CommentClassification
    sentiment: CommentSentiment
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: CommentStatus
    escalated: bool
    is_hidden: bool
    received_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateReplyRequest(BaseModel):
    """Schema for creating a reply."""
    text: str = Field(..., min_length=1, max_length=1000, description="Reply text")


class ReplyResponse(BaseModel):
    """Schema for reply response."""
    id: str
    comment_id: str
    reply_text: str
    status: CommentReplyStatus
    generated_by_agent: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class ClassificationResponse(BaseModel):
    """Schema for classification result."""
    comment_id: str
    classification: str
    sentiment: str
    confidence: float
    reasoning: str
    is_sensitive: bool


class EscalationRequest(BaseModel):
    """Schema for escalation request."""
    reason: str = Field(..., min_length=1, description="Reason for escalation")


class EscalationResponse(BaseModel):
    """Schema for escalation response."""
    success: bool
    comment_id: str
    escalated: bool
    status: str


class SendReplyResponse(BaseModel):
    """Schema for send reply response."""
    success: bool
    reply_id: str
    status: str


class WebhookPayload(BaseModel):
    """Schema for webhook payload."""
    object: str
    entry: List[Dict[str, Any]]
    hub_mode: Optional[str] = None
    hub_challenge: Optional[str] = None
    hub_verify_token: Optional[str] = None


class WebhookResult(BaseModel):
    """Schema for webhook processing result."""
    comment_id: str
    platform_comment_id: str
    classification: str
    requires_approval: bool
    escalated: bool


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    success: bool
    processed: int
    results: List[WebhookResult]


class CommentStatsResponse(BaseModel):
    """Schema for comment statistics."""
    total_comments: int
    by_status: Dict[str, int]
    by_classification: Dict[str, int]
    escalated_count: int
    responded_count: int
    response_rate: float


class PendingReplyResponse(BaseModel):
    """Schema for pending reply."""
    id: str
    comment_id: str
    reply_text: str
    created_at: datetime


class CommentFilter(BaseModel):
    """Schema for comment filtering."""
    post_id: Optional[str] = None
    status: Optional[str] = None
    classification: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class BulkActionRequest(BaseModel):
    """Schema for bulk action request."""
    comment_ids: List[str] = Field(..., min_length=1)
    action: str = Field(..., pattern="^(escalate|hide|ignore|approve)$")


class BulkActionResponse(BaseModel):
    """Schema for bulk action response."""
    success: bool
    processed: int
    failed: int
    results: List[Dict[str, Any]]
