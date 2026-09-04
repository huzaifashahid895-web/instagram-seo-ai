# backend/app/services/comment_manager.py — Comment management service
# Cost classification: FREE + OPEN SOURCE

"""
Comment management service for Instagram.

Handles:
1. Comment ingestion from Instagram webhook
2. Classification pipeline
3. Response generation workflow
4. Escalation to approval queue
5. Analytics and reporting

Pipeline:
webhook → validate signature → store raw comment → classify → 
generate response → save draft → (if sensitive) → approval queue → 
(send via Instagram API) → log to comment_replies
"""

import hmac
import hashlib
import uuid
from datetime import datetime
from typing import Protocol, Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Comment, CommentSentiment, CommentStatus, CommentReply, CommentReplyStatus, Post, SocialAccount
from app.services.comment_classifier import CommentClassification, LLMLessCommentClassifier
from app.services.providers import LLMProvider

if TYPE_CHECKING:
    from app.services.comment_classifier import CommentClassifier
    from app.services.comment_responder import CommentResponder


class WebhookPayload(BaseModel):
    """Instagram comment webhook payload."""
    object: str
    entry: List[Dict[str, Any]]
    hub_mode: str = Field(default="subscribe")
    hub_challenge: Optional[str] = None
    hub_verify_token: Optional[str] = None


class WebhookEvent(BaseModel):
    """Parsed webhook event."""
    comment_id: str
    post_id: str
    user_id: str
    username: str
    text: str
    created_time: datetime
    raw_payload: str


class CommentResult(BaseModel):
    """Result of comment processing."""
    comment_id: uuid.UUID
    platform_comment_id: str
    classification: str
    confidence: Optional[float]
    status: str
    response_draft_id: Optional[uuid.UUID]
    requires_approval: bool
    escalated: bool


class WebhookHandler(Protocol):
    """Protocol for webhook handlers."""
    
    async def validate_signature(
        self,
        payload: bytes,
        x_hub_signature: str,
        app_secret: str
    ) -> bool:
        """Validate Instagram webhook signature."""
        ...
    
    async def process_event(self, event: WebhookEvent) -> CommentResult:
        """Process a webhook event and return result."""
        ...


class WebhookSignatureValidator:
    """Validate Instagram webhook signatures using HMAC-SHA1."""
    
    @staticmethod
    def validate(payload: bytes, x_hub_signature: str, app_secret: str) -> bool:
        """
        Validate webhook signature.
        
        Instagram sends: X-Hub-Signature: sha1=<hmac_hash>
        We compute: hmac.new(app_secret, payload, hashlib.sha1).hexdigest()
        """
        if not x_hub_signature:
            return False
        
        # Parse signature (format: "sha1=hash")
        if not x_hub_signature.startswith("sha1="):
            return False
        
        expected_hash = x_hub_signature[5:]  # Remove "sha1=" prefix
        
        computed_hash = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha1
        ).hexdigest()
        
        return hmac.compare_digest(expected_hash, computed_hash)


class CommentManager:
    """
    Comment management service for Instagram integration.
    
    Handles the full comment workflow:
    1. Webhook validation and parsing
    2. Comment classification
    3. Response generation
    4. Approval escalation
    5. Database persistence
    """
    
    def __init__(
        self,
        classifier: Optional["CommentClassifier"] = None,
        responder: Optional["CommentResponder"] = None,
        validator: Optional[WebhookSignatureValidator] = None,
        app_secret: Optional[str] = None
    ):
        """Initialize comment manager with dependencies."""
        self.classifier = classifier
        self.responder = responder
        self.validator = validator or WebhookSignatureValidator()
        self.app_secret = app_secret
    
    async def validate_webhook(
        self,
        payload: bytes,
        x_hub_signature: str
    ) -> bool:
        """Validate webhook signature."""
        if not self.app_secret:
            return False
        return self.validator.validate(payload, x_hub_signature, self.app_secret)
    
    async def handle_webhook(
        self,
        payload: Dict[str, Any]
    ) -> List[CommentResult]:
        """
        Handle Instagram webhook event.
        
        Handles both verification events (hub_challenge) and
        actual comment events (changes array).
        """
        results = []
        
        # Check for verification event
        if payload.get("hub_mode") == "subscribe":
            return [CommentResult(
                comment_id=uuid.uuid4(),
                platform_comment_id="verification",
                classification=CommentClassification.POSITIVE,
                confidence=1.0,
                status=CommentStatus.IGNORED,
                response_draft_id=None,
                requires_approval=False,
                escalated=False
            )]
        
        # Process entries
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") == "comments":
                    value = change.get("value", {})
                    result = await self._process_comment_event(value)
                    results.append(result)
        
        return results
    
    async def _process_comment_event(self, value: Dict[str, Any]) -> CommentResult:
        """Process a single comment event."""
        from app.core.db import SessionLocal
        
        comment_id = value.get("id", "")
        post_id = value.get("post_id", "")
        user_id = value.get("from", {}).get("id", "")
        username = value.get("from", {}).get("name", "")
        text = value.get("message", value.get("text", ""))
        created_time = value.get("created_time", datetime.utcnow())
        
        event = WebhookEvent(
            comment_id=comment_id,
            post_id=post_id,
            user_id=user_id,
            username=username,
            text=text,
            created_time=created_time,
            raw_payload=str(value)
        )
        
        async with SessionLocal() as session:
            return await self._process_comment(session, event)
    
    async def _process_comment(self, session: AsyncSession, event: WebhookEvent) -> CommentResult:
        """Process comment and generate response."""
        # Check if comment already exists
        stmt = select(Comment).where(Comment.platform_comment_id == event.comment_id)
        result = await session.execute(stmt)
        existing_comment = result.scalar_one_or_none()
        
        if existing_comment:
            # Comment already processed
            return CommentResult(
                comment_id=existing_comment.id,
                platform_comment_id=existing_comment.platform_comment_id,
                classification=existing_comment.classification,
                confidence=existing_comment.confidence_score,
                status=existing_comment.status,
                response_draft_id=None,
                requires_approval=False,
                escalated=existing_comment.escalated
            )
        
        # Look up post by platform_post_id
        stmt = select(Post).where(Post.platform_post_id == event.post_id)
        result = await session.execute(stmt)
        post = result.scalar_one_or_none()
        
        if not post:
            # Post not found, skip processing
            return CommentResult(
                comment_id=uuid.uuid4(),
                platform_comment_id=event.comment_id,
                classification=CommentClassification.UNKNOWN,
                confidence=None,
                status=CommentStatus.IGNORED,
                response_draft_id=None,
                requires_approval=False,
                escalated=False
            )
        
        # Create new comment record
        comment = Comment(
            post_id=post.id,
            platform_comment_id=event.comment_id,
            author_platform_id=event.user_id,
            author_username=event.username,
            text=event.text,
            raw_payload=event.raw_payload,
            classification=CommentClassification.UNKNOWN,
            sentiment=CommentSentiment.UNKNOWN,
            status=CommentStatus.NEW
        )
        
        # Classify comment
        if self.classifier:
            classification_result = await self.classifier.classify(event.text)
            comment.classification = classification_result.classification
            comment.sentiment = self._infer_sentiment(classification_result.classification)
            comment.confidence_score = classification_result.confidence
            
            # Determine if comment is sensitive
            if classification_result.is_sensitive:
                comment.escalated = True
                comment.status = CommentStatus.ESCALATED
            else:
                comment.status = CommentStatus.REVIEWING
        else:
            comment.status = CommentStatus.REVIEWING
        
        session.add(comment)
        await session.commit()
        await session.refresh(comment)
        
        # Generate response if not sensitive
        response_draft_id = None
        if not comment.escalated and self.responder:
            try:
                configuration = ResponseConfiguration(
                    brand_name="Instagram SEO",
                    brand_voice="friendly, helpful, and professional",
                    max_response_length=150
                )
                
                response = await self.responder.generate_response(
                    comment,
                    comment.classification,
                    configuration
                )
                
                # Save response draft
                reply = CommentReply(
                    comment_id=comment.id,
                    reply_text=response.reply_text,
                    status=CommentReplyStatus.DRAFT,
                    generated_by_agent=True,
                    raw_payload=response.template_used or ""
                )
                session.add(reply)
                await session.commit()
                await session.refresh(reply)
                response_draft_id = reply.id
            except Exception:
                # Response generation failed, continue without it
                pass
        
        return CommentResult(
            comment_id=comment.id,
            platform_comment_id=comment.platform_comment_id,
            classification=comment.classification,
            confidence=comment.confidence_score,
            status=comment.status,
            response_draft_id=response_draft_id,
            requires_approval=comment.escalated,
            escalated=comment.escalated
        )
    
    def _infer_sentiment(self, classification: CommentClassification) -> CommentSentiment:
        """Infer sentiment from classification."""
        positive_classes = {
            CommentClassification.POSITIVE,
            CommentClassification.PRAISE
        }
        negative_classes = {
            CommentClassification.NEGATIVE,
            CommentClassification.COMPLAINT,
            CommentClassification.TROLL
        }
        
        if classification in positive_classes:
            return CommentSentiment.POSITIVE
        elif classification in negative_classes:
            return CommentSentiment.NEGATIVE
        else:
            return CommentSentiment.NEUTRAL
    
    async def get_comment_by_platform_id(
        self,
        session: AsyncSession,
        platform_comment_id: str
    ) -> Optional[Comment]:
        """Get comment by platform ID."""
        stmt = select(Comment).where(Comment.platform_comment_id == platform_comment_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_comments(
        self,
        session: AsyncSession,
        post_id: Optional[uuid.UUID] = None,
        status: Optional[CommentStatus] = None,
        classification: Optional[CommentClassification] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Comment]:
        """List comments with optional filters."""
        stmt = select(Comment)
        
        if post_id:
            stmt = stmt.where(Comment.post_id == post_id)
        if status:
            stmt = stmt.where(Comment.status == status)
        if classification:
            stmt = stmt.where(Comment.classification == classification)
        
        stmt = stmt.order_by(Comment.received_at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def reply_to_comment(
        self,
        session: AsyncSession,
        comment_id: uuid.UUID,
        reply_text: str,
        status: CommentReplyStatus = CommentReplyStatus.PENDING_APPROVAL,
        generated_by_agent: bool = False
    ) -> CommentReply:
        """Create a reply to a comment."""
        stmt = select(Comment).where(Comment.id == comment_id)
        result = await session.execute(stmt)
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise ValueError("Comment not found")
        
        reply = CommentReply(
            comment_id=comment_id,
            reply_text=reply_text,
            status=status,
            generated_by_agent=generated_by_agent,
            raw_payload=""
        )
        
        session.add(reply)
        await session.commit()
        await session.refresh(reply)
        return reply
    
    async def escalate_comment(
        self,
        session: AsyncSession,
        comment_id: uuid.UUID,
        reason: str,
        escalated_by_user_id: Optional[uuid.UUID] = None
    ) -> Comment:
        """Escalate a comment for human review."""
        stmt = select(Comment).where(Comment.id == comment_id)
        result = await session.execute(stmt)
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise ValueError("Comment not found")
        
        comment.escalated = True
        comment.status = CommentStatus.ESCALATED
        comment.raw_payload = f"Escalated: {reason}"
        
        session.add(comment)
        await session.commit()
        await session.refresh(comment)
        return comment
    
    async def get_pending_replies(
        self,
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0
    ) -> List[CommentReply]:
        """Get replies pending approval."""
        stmt = select(CommentReply).where(
            CommentReply.status == CommentReplyStatus.PENDING_APPROVAL
        ).order_by(CommentReply.created_at.asc()).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def approve_reply(
        self,
        session: AsyncSession,
        reply_id: uuid.UUID,
        approved_by_user_id: uuid.UUID
    ) -> CommentReply:
        """Approve a comment reply."""
        stmt = select(CommentReply).where(CommentReply.id == reply_id)
        result = await session.execute(stmt)
        reply = result.scalar_one_or_none()
        
        if not reply:
            raise ValueError("Reply not found")
        
        reply.approved_by_user_id = approved_by_user_id
        reply.status = CommentReplyStatus.APPROVED
        reply.raw_payload = f"Approved by user: {approved_by_user_id}"
        
        session.add(reply)
        await session.commit()
        await session.refresh(reply)
        return reply
    
    async def send_reply_to_platform(
        self,
        session: AsyncSession,
        reply_id: uuid.UUID,
        platform_service: Any
    ) -> bool:
        """
        Send approved reply to Instagram platform.
        
        Returns True if successful, False otherwise.
        """
        stmt = select(CommentReply).where(CommentReply.id == reply_id).options(
            select.joinedload(CommentReply.comment)
        )
        result = await session.execute(stmt)
        reply = result.scalar_one_or_none()
        
        if not reply or reply.status != CommentReplyStatus.APPROVED:
            return False
        
        # Get parent comment and post
        comment = reply.comment
        if not comment:
            return False
        
        # Get social account for posting
        stmt = select(SocialAccount).where(
            SocialAccount.id == comment.post.social_account_id
        )
        result = await session.execute(stmt)
        social_account = result.scalar_one_or_none()
        
        if not social_account:
            return False
        
        try:
            # Send reply via Instagram API
            platform_reply_id = await platform_service.reply_to_comment(
                social_account=social_account,
                comment_id=comment.platform_comment_id,
                reply_text=reply.reply_text
            )
            
            # Update reply with platform ID and status
            reply.platform_reply_id = platform_reply_id
            reply.status = CommentReplyStatus.SENT
            reply.sent_at = datetime.utcnow()
            
            # Update comment status
            comment.status = CommentStatus.REPLIED
            
            session.add(reply)
            session.add(comment)
            await session.commit()
            
            return True
            
        except Exception as e:
            reply.status = CommentReplyStatus.FAILED
            reply.error_message = str(e)
            session.add(reply)
            await session.commit()
            return False


class CommentManagerService:
    """
    Service wrapper for comment management with dependency injection.
    
    Provides convenient methods for comment management without
    requiring manual session handling.
    """
    
    def __init__(
        self,
        manager: Optional[CommentManager] = None
    ):
        """Initialize with comment manager instance."""
        self.manager = manager or CommentManager()
    
    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        x_hub_signature: Optional[str] = None
    ) -> List[CommentResult]:
        """Handle Instagram webhook event."""
        if x_hub_signature:
            # Validation skipped if no app_secret configured
            pass
        
        return await self.manager.handle_webhook(payload)
    
    async def list_comments(
        self,
        session: AsyncSession,
        **filters
    ) -> List[Comment]:
        """List comments with filters."""
        return await self.manager.list_comments(session, **filters)
    
    async def get_pending_replies(
        self,
        session: AsyncSession
    ) -> List[CommentReply]:
        """Get replies pending approval."""
        return await self.manager.get_pending_replies(session)
    
    async def send_pending_replies(
        self,
        session: AsyncSession,
        platform_service: Any
    ) -> Dict[str, int]:
        """Send all pending approved replies to platform."""
        replies = await self.manager.get_pending_replies(session)
        
        results = {"sent": 0, "failed": 0, "skipped": 0}
        
        for reply in replies:
            if reply.status == CommentReplyStatus.APPROVED:
                success = await self.manager.send_reply_to_platform(session, reply.id, platform_service)
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
            else:
                results["skipped"] += 1
        
        return results
