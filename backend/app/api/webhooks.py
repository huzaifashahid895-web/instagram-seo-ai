# backend/app/api/webhooks.py
# Cost classification: FREE, REQUIRES INTERNET
"""
Webhook handlers for Instagram and other platform events.

Instagram webhooks require:
1. HTTPS endpoint (for production)
2. Webhook subscription via Meta App Dashboard
3. Verification token matching
4. Event signature validation
"""

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# Webhook event models
class InstagramCommentEvent(BaseModel):
    """Instagram comment webhook event."""
    id: str  # Comment ID
    text: str
    from_user: dict = {}  # {"id": "...", "username": "..."}
    media_id: str
    timestamp: str


class InstagramMentionEvent(BaseModel):
    """Instagram mention webhook event."""
    id: str  # Media ID where mentioned
    caption: str | None = None
    media_type: str  # IMAGE, VIDEO, CAROUSEL_ALBUM
    from_user: dict = {}
    timestamp: str


@router.get("/instagram")
async def instagram_webhook_verify(request: Request) -> Response:
    """
    Verify Instagram webhook subscription.
    
    Instagram sends a GET request with:
    - hub.mode=subscribe
    - hub.challenge=<random_string>
    - hub.verify_token=<your_token>
    
    You must return the challenge value if verify_token matches.
    
    Setup:
    1. Go to Meta App Dashboard → Products → Webhooks
    2. Subscribe to instagram topic
    3. Set callback URL: https://your-domain.com/webhooks/instagram
    4. Set verify token in .env: INSTAGRAM_WEBHOOK_VERIFY_TOKEN
    """
    params = request.query_params
    
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    logger.info(f"Instagram webhook verification: mode={mode}, token_match={token == settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN}")
    
    if mode == "subscribe" and token == settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN:
        logger.info("Instagram webhook verification successful")
        return Response(content=challenge, media_type="text/plain")
    else:
        logger.warning("Instagram webhook verification failed: invalid token")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification token mismatch"
        )


@router.post("/instagram")
async def instagram_webhook_event(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Handle Instagram webhook events.
    
    Supported events:
    - comments: New comment on your post
    - mentions: You were mentioned in another post
    - story_insights: Story metrics available
    
    Event structure:
    {
      "object": "instagram",
      "entry": [
        {
          "id": "<INSTAGRAM_BUSINESS_ACCOUNT_ID>",
          "time": <TIMESTAMP>,
          "changes": [
            {
              "field": "comments",
              "value": {
                "id": "<COMMENT_ID>",
                "text": "Comment text",
                "from": {"id": "...", "username": "..."},
                "media": {"id": "<MEDIA_ID>"}
              }
            }
          ]
        }
      ]
    }
    """
    # Verify signature (production requirement)
    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    if settings.INSTAGRAM_APP_SECRET and not _verify_signature(body_bytes, signature, settings.INSTAGRAM_APP_SECRET):
        logger.warning("Instagram webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature"
        )
    
    # Parse event
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        logger.error("Failed to parse Instagram webhook body")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )
    
    # Process events
    if data.get("object") != "instagram":
        logger.warning(f"Unexpected webhook object type: {data.get('object')}")
        return {"status": "ignored"}
    
    for entry in data.get("entry", []):
        instagram_account_id = entry.get("id")
        timestamp = entry.get("time")
        
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})
            
            logger.info(f"Instagram webhook event: {field} for account {instagram_account_id}")
            
            if field == "comments":
                await _handle_comment_event(instagram_account_id, value, db)
            
            elif field == "mentions":
                await _handle_mention_event(instagram_account_id, value, db)
            
            elif field == "story_insights":
                await _handle_story_insights_event(instagram_account_id, value, db)
            
            else:
                logger.info(f"Unhandled webhook field: {field}")
    
    return {"status": "ok"}


async def _handle_comment_event(account_id: str, value: dict, db: Session):
    """
    Handle new comment event.
    
    Actions:
    - Log comment for moderation
    - Check for spam/inappropriate content
    - Trigger auto-reply if configured
    - Store in comments table for analytics
    """
    comment_id = value.get("id")
    comment_text = value.get("text", "")
    media_id = value.get("media", {}).get("id")
    from_user = value.get("from", {})
    
    logger.info(f"New comment on media {media_id}: {comment_text[:50]}... by {from_user.get('username')}")
    
    # TODO: Implement comment processing
    # - Store in Comment model
    # - Check for spam/inappropriate content
    # - Trigger auto-reply if rules match
    # - Send notification to user
    
    pass


async def _handle_mention_event(account_id: str, value: dict, db: Session):
    """
    Handle mention event (tagged in another user's post).
    
    Actions:
    - Log mention for engagement tracking
    - Store in mentions table
    - Send notification to user
    """
    media_id = value.get("id")
    caption = value.get("caption", "")
    from_user = value.get("from", {})
    
    logger.info(f"Mentioned in media {media_id} by {from_user.get('username')}")
    
    # TODO: Implement mention processing
    # - Store mention record
    # - Send notification
    # - Track for engagement metrics
    
    pass


async def _handle_story_insights_event(account_id: str, value: dict, db: Session):
    """
    Handle story insights event.
    
    Triggered when story metrics become available (after 24h).
    
    Actions:
    - Fetch story insights via Graph API
    - Store in analytics table
    """
    media_id = value.get("media_id")
    
    logger.info(f"Story insights available for media {media_id}")
    
    # TODO: Implement story insights collection
    # - Fetch insights via Instagram Graph API
    # - Store in Analytics model
    
    pass


def _verify_signature(body: bytes, signature: str, app_secret: str) -> bool:
    """
    Verify Instagram webhook signature.
    
    Instagram signs requests with HMAC-SHA256 using your app secret.
    The signature is sent in X-Hub-Signature-256 header as: sha256=<hex>
    
    Args:
        body: Raw request body
        signature: X-Hub-Signature-256 header value
        app_secret: Instagram app secret
        
    Returns:
        True if signature is valid
    """
    if not signature.startswith("sha256="):
        return False
    
    expected_signature = signature[7:]  # Remove "sha256=" prefix
    
    computed_signature = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, expected_signature)


@router.get("/health")
async def webhook_health() -> dict:
    """
    Webhook health check endpoint.
    
    Returns webhook configuration status.
    """
    return {
        "status": "ok",
        "webhooks": {
            "instagram": {
                "verify_token_configured": bool(settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN),
                "app_secret_configured": bool(settings.INSTAGRAM_APP_SECRET),
                "signature_verification": "enabled" if settings.INSTAGRAM_APP_SECRET else "disabled",
            }
        },
        "setup_instructions": {
            "1": "Set INSTAGRAM_WEBHOOK_VERIFY_TOKEN in .env",
            "2": "Set INSTAGRAM_APP_SECRET in .env",
            "3": "Subscribe to webhook in Meta App Dashboard",
            "4": "Configure callback URL: https://your-domain.com/webhooks/instagram",
        }
    }
