# backend/app/api/comments.py — Comments API endpoints
# Cost classification: FREE + OPEN SOURCE

"""
Comments API endpoints for Instagram comment management.

Endpoints:
- GET /comments - List comments (with filters)
- GET /comments/{id} - Get comment details
- POST /comments/webhook - Instagram webhook handler
- POST /comments/{id}/reply - Create reply
- POST /comments/{id}/escalate - Escalate for approval
- POST /comments/{id}/send-reply - Send approved reply to Instagram
- GET /comments/stats - Comment statistics
- GET /comments/pending-replies - Get pending replies for approval
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Header
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import (
    Comment, CommentClassification, CommentSentiment, CommentStatus,
    CommentReply, CommentReplyStatus
)
from app.schemas import comments as comment_schemas
from app.services.comment_manager import CommentManager, CommentManagerService
from app.services.comment_classifier import CommentClassifier, LLMLessCommentClassifier
from app.services.comment_responder import CommentResponder, ResponseConfiguration
from app.services.platforms.instagram import InstagramPlatform

router = APIRouter(prefix="/comments", tags=["Comments"])


# Service dependencies
def get_comment_manager(
    session: Session = Depends(get_db)
) -> CommentManagerService:
    """Get comment manager service instance."""
    classifier = LLMLessCommentClassifier()
    responder = CommentResponder()
    manager = CommentManager(classifier=classifier, responder=responder)
    return CommentManagerService(manager=manager)


@router.get("/", response_model=List[comment_schemas.CommentResponse])
async def list_comments(
    post_id: Optional[str] = None,
    status: Optional[str] = None,
    classification: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db)
):
    """
    List comments with optional filters.
    
    - **post_id**: Filter by post ID (platform ID)
    - **status**: Filter by status (new, reviewing, replied, escalated)
    - **classification**: Filter by classification
    - **limit**: Maximum results (default: 50)
    - **offset**: Pagination offset (default: 0)
    """
    from sqlalchemy.future import select
    from app.models import Comment
    
    stmt = select(Comment)
    
    if post_id:
        stmt = stmt.where(Comment.platform_comment_id == post_id)
    if status:
        stmt = stmt.where(Comment.status == CommentStatus(status))
    if classification:
        stmt = stmt.where(Comment.classification == CommentClassification(classification))
    
    stmt = stmt.order_by(Comment.received_at.desc()).limit(limit).offset(offset)
    
    result = await session.execute(stmt)
    comments = result.scalars().all()
    
    return [
        comment_schemas.CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            platform_comment_id=comment.platform_comment_id,
            author_platform_id=comment.author_platform_id,
            author_username=comment.author_username,
            text=comment.text,
            classification=comment.classification,
            sentiment=comment.sentiment,
            confidence_score=comment.confidence_score,
            status=comment.status,
            escalated=comment.escalated,
            is_hidden=comment.is_hidden,
            received_at=comment.received_at,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )
        for comment in comments
    ]


@router.get("/{comment_id}", response_model=comment_schemas.CommentResponse)
async def get_comment(
    comment_id: str,
    session: Session = Depends(get_db)
):
    """Get comment by ID."""
    from sqlalchemy.future import select
    
    stmt = select(Comment).where(Comment.id == comment_id)
    result = await session.execute(stmt)
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    return comment_schemas.CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        platform_comment_id=comment.platform_comment_id,
        author_platform_id=comment.author_platform_id,
        author_username=comment.author_username,
        text=comment.text,
        classification=comment.classification,
        sentiment=comment.sentiment,
        confidence_score=comment.confidence_score,
        status=comment.status,
        escalated=comment.escalated,
        is_hidden=comment.is_hidden,
        received_at=comment.received_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )


@router.post("/webhook", response_model=comment_schemas.WebhookResponse)
async def handle_webhook(
    payload: dict = Body(...),
    x_hub_signature: Optional[str] = Header(None, alias="X-Hub-Signature"),
    manager: CommentManagerService = Depends(get_comment_manager)
):
    """
    Handle Instagram comment webhook.
    
    This endpoint receives comment notifications from Instagram:
    - Comment creation on posts
    - Comment replies
    
    Returns the processing result for each comment.
    """
    try:
        results = await manager.handle_webhook(
            payload=payload,
            x_hub_signature=x_hub_signature
        )
        
        return comment_schemas.WebhookResponse(
            success=True,
            processed=len(results),
            results=[
                comment_schemas.WebhookResult(
                    comment_id=str(result.comment_id),
                    platform_comment_id=result.platform_comment_id,
                    classification=result.classification.value,
                    requires_approval=result.requires_approval,
                    escalated=result.escalated
                )
                for result in results
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.post("/{comment_id}/reply", response_model=comment_schemas.ReplyResponse)
async def create_reply(
    comment_id: str,
    payload: comment_schemas.CreateReplyRequest,
    session: Session = Depends(get_db)
):
    """
    Create a reply to a comment.
    
    Can be used for:
    - Human-crafted responses
    - Agent-generated responses (after approval)
    """
    from app.models import CommentReply, CommentReplyStatus
    from sqlalchemy.future import select
    
    # Check comment exists
    stmt = select(Comment).where(Comment.id == comment_id)
    result = await session.execute(stmt)
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Create reply
    reply = CommentReply(
        comment_id=comment.id,
        reply_text=payload.text,
        status=CommentReplyStatus.DRAFT,
        generated_by_agent=False,
        raw_payload=""
    )
    
    session.add(reply)
    await session.commit()
    await session.refresh(reply)
    
    return comment_schemas.ReplyResponse(
        id=reply.id,
        comment_id=str(reply.comment_id),
        reply_text=reply.reply_text,
        status=reply.status,
        generated_by_agent=reply.generated_by_agent,
        created_at=reply.created_at
    )


@router.post("/{comment_id}/classify", response_model=comment_schemas.ClassificationResponse)
async def classify_comment(
    comment_id: str,
    session: Session = Depends(get_db)
):
    """
    Classify a comment.
    
    Uses the rule-based classifier to automatically categorize
    the comment and update its classification.
    """
    from sqlalchemy.future import select
    from app.services.comment_classifier import LLMLessCommentClassifier
    
    stmt = select(Comment).where(Comment.id == comment_id)
    result = await session.execute(stmt)
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    classifier = LLMLessCommentClassifier()
    result = await classifier.classify(comment.text)
    
    comment.classification = result.classification
    comment.confidence_score = result.confidence
    
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    
    return comment_schemas.ClassificationResponse(
        comment_id=str(comment.id),
        classification=comment.classification.value,
        sentiment=comment.sentiment.value,
        confidence=comment.confidence_score,
        reasoning=result.reasoning,
        is_sensitive=result.is_sensitive
    )


@router.post("/{comment_id}/escalate", response_model=comment_schemas.EscalationResponse)
async def escalate_comment(
    comment_id: str,
    payload: comment_schemas.EscalationRequest,
    session: Session = Depends(get_db)
):
    """
    Escalate a comment for human review.
    
    Escalated comments require manual approval before any
    automated response is sent.
    """
    from sqlalchemy.future import select
    from app.models import Comment
    
    stmt = select(Comment).where(Comment.id == comment_id)
    result = await session.execute(stmt)
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.escalated = True
    comment.status = CommentStatus.ESCALATED
    comment.raw_payload = f"Escalated: {payload.reason}"
    
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    
    return comment_schemas.EscalationResponse(
        success=True,
        comment_id=str(comment.id),
        escalated=comment.escalated,
        status=comment.status
    )


@router.post("/{comment_id}/send-reply", response_model=comment_schemas.SendReplyResponse)
async def send_reply(
    comment_id: str,
    session: Session = Depends(get_db)
):
    """
    Send a pending reply to Instagram.
    
    Sends an approved reply via the Instagram Graph API.
    """
    from sqlalchemy.future import select
    from app.models import CommentReply, CommentReplyStatus
    from app.services.platforms.instagram import InstagramPlatform
    
    stmt = select(CommentReply).where(CommentReply.id == comment_id).options(
        select.joinedload(CommentReply.comment)
    )
    result = await session.execute(stmt)
    reply = result.scalar_one_or_none()
    
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    
    if reply.status != CommentReplyStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Reply must be approved before sending")
    
    # Get Instagram platform service
    platform = InstagramPlatform()
    
    try:
        success = await platform.send_reply_to_platform(session, reply.id, platform)
        
        if success:
            return comment_schemas.SendReplyResponse(
                success=True,
                reply_id=str(reply.id),
                status=reply.status
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to send reply")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reply: {str(e)}")


@router.get("/stats", response_model=comment_schemas.CommentStatsResponse)
async def get_comment_stats(
    session: Session = Depends(get_db)
):
    """
    Get comment statistics and metrics.
    
    Returns:
    - Total comments
    - Comments by status
    - Comments by classification
    - Response rate
    """
    from sqlalchemy.future import select
    from sqlalchemy import func
    
    # Total comments
    total_stmt = select(func.count(Comment.id))
    total_result = await session.execute(total_stmt)
    total_comments = total_result.scalar_one()
    
    # By status
    status_stmt = select(
        Comment.status,
        func.count(Comment.id).label("count")
    ).group_by(Comment.status)
    status_result = await session.execute(status_stmt)
    status_counts = {row.status.value: row.count for row in status_result}
    
    # By classification
    class_stmt = select(
        Comment.classification,
        func.count(Comment.id).label("count")
    ).group_by(Comment.classification)
    class_result = await session.execute(class_stmt)
    class_counts = {row.classification.value: row.count for row in class_result}
    
    # Escalated count
    escalated_stmt = select(func.count(Comment.id)).where(Comment.escalated == True)
    escalated_result = await session.execute(escalated_stmt)
    escalated_count = escalated_result.scalar_one()
    
    # With responses
    response_stmt = select(func.count(Comment.id)).where(
        Comment.status == CommentStatus.REPLIED
    )
    response_result = await session.execute(response_stmt)
    responded_count = response_result.scalar_one()
    
    return comment_schemas.CommentStatsResponse(
        total_comments=total_comments,
        by_status=status_counts,
        by_classification=class_counts,
        escalated_count=escalated_count,
        responded_count=responded_count,
        response_rate=responded_count / total_comments if total_comments > 0 else 0
    )


@router.get("/pending-replies", response_model=List[comment_schemas.PendingReplyResponse])
async def get_pending_replies(
    session: Session = Depends(get_db)
):
    """Get replies that need human approval."""
    from sqlalchemy.future import select
    from app.models import CommentReply
    
    stmt = select(CommentReply).where(
        CommentReply.status == CommentReplyStatus.PENDING_APPROVAL
    ).order_by(CommentReply.created_at.asc())
    
    result = await session.execute(stmt)
    replies = result.scalars().all()
    
    return [
        comment_schemas.PendingReplyResponse(
            id=reply.id,
            comment_id=str(reply.comment_id),
            reply_text=reply.reply_text,
            created_at=reply.created_at
        )
        for reply in replies
    ]
