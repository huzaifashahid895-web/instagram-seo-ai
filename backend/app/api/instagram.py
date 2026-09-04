# backend/app/api/instagram.py
# Cost classification: FREE, REQUIRES INTERNET
"""
Instagram API endpoints for publishing, comments, and analytics.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.social_account import SocialAccount
from app.services.platforms.instagram import InstagramPlatform
from app.services.providers import PublishResult, Comment, PostAnalytics

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class PublishPostRequest(BaseModel):
    """Request to publish an image post to Instagram."""
    social_account_id: str = Field(..., description="Social account ID to publish from")
    image_url: str = Field(..., description="Public URL to the image")
    caption: str | None = Field(None, max_length=2200, description="Post caption")
    location_id: str | None = Field(None, description="Facebook Page ID for location")


class PublishReelRequest(BaseModel):
    """Request to publish a reel to Instagram."""
    social_account_id: str = Field(..., description="Social account ID to publish from")
    video_url: str = Field(..., description="Public URL to the video")
    caption: str | None = Field(None, max_length=2200, description="Reel caption")
    cover_url: str | None = Field(None, description="Custom cover image URL")
    share_to_feed: bool = Field(True, description="Share reel to main feed")


class GetCommentsRequest(BaseModel):
    """Request to fetch comments for a post."""
    social_account_id: str = Field(..., description="Social account ID")
    post_id: str = Field(..., description="Instagram post ID")
    limit: int = Field(50, ge=1, le=50, description="Max comments to fetch")


class ReplyToCommentRequest(BaseModel):
    """Request to reply to a comment."""
    social_account_id: str = Field(..., description="Social account ID")
    comment_id: str = Field(..., description="Instagram comment ID")
    text: str = Field(..., min_length=1, max_length=500, description="Reply text")


class HideCommentRequest(BaseModel):
    """Request to hide a comment."""
    social_account_id: str = Field(..., description="Social account ID")
    comment_id: str = Field(..., description="Instagram comment ID")


class DeleteCommentRequest(BaseModel):
    """Request to delete a comment."""
    social_account_id: str = Field(..., description="Social account ID")
    comment_id: str = Field(..., description="Instagram comment ID")


class GetAnalyticsRequest(BaseModel):
    """Request to fetch analytics for a post."""
    social_account_id: str = Field(..., description="Social account ID")
    post_id: str = Field(..., description="Instagram post ID")


# Dependency: Get Instagram platform instance from social account
def get_instagram_platform(
    social_account_id: str,
    current_user: User,
    db: Session,
) -> InstagramPlatform:
    """
    Get Instagram platform service for a social account.
    
    Args:
        social_account_id: Social account UUID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        InstagramPlatform instance
        
    Raises:
        HTTPException: If account not found or invalid
    """
    # Fetch social account
    stmt = select(SocialAccount).where(
        SocialAccount.id == social_account_id,
        SocialAccount.user_id == current_user.id,
        SocialAccount.platform == "instagram",
        SocialAccount.is_active == True,
    )
    social_account = db.scalar(stmt)
    
    if not social_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instagram account not found or inactive"
        )
    
    if not social_account.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instagram account has no valid access token"
        )
    
    if not social_account.platform_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instagram account missing platform user ID"
        )
    
    return InstagramPlatform(
        access_token=social_account.access_token,
        instagram_user_id=social_account.platform_user_id,
    )


@router.post("/publish/post", response_model=PublishResult)
def publish_post(
    request: PublishPostRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PublishResult:
    """
    Publish an image post to Instagram.
    
    Requirements:
    - Image must be publicly accessible URL
    - Supported formats: JPG, PNG
    - Min resolution: 320x320px
    - Max file size: 8MB
    - Caption max: 2200 characters
    """
    logger.info(f"Publishing Instagram post for user {current_user.id}")
    
    instagram = get_instagram_platform(
        social_account_id=request.social_account_id,
        current_user=current_user,
        db=db,
    )
    
    try:
        result = instagram.publish_post(
            image_url=request.image_url,
            caption=request.caption,
            location_id=request.location_id,
        )
        
        logger.info(f"Successfully published Instagram post: {result.platform_post_id}")
        return result
    
    except Exception as e:
        logger.error(f"Failed to publish Instagram post: {e}", exc_info=True)
        raise


@router.post("/publish/reel", response_model=PublishResult)
def publish_reel(
    request: PublishReelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PublishResult:
    """
    Publish a reel to Instagram.
    
    Requirements:
    - Video must be publicly accessible URL
    - Format: MP4
    - Duration: 3-90 seconds (15-60s recommended)
    - Min resolution: 540x960px
    - Max file size: 1GB
    - Aspect ratio: 9:16 (vertical)
    - Caption max: 2200 characters
    
    Note: Video processing can take 1-5 minutes. This endpoint waits for completion.
    """
    logger.info(f"Publishing Instagram reel for user {current_user.id}")
    
    instagram = get_instagram_platform(
        social_account_id=request.social_account_id,
        current_user=current_user,
        db=db,
    )
    
    try:
        result = instagram.publish_video(
            video_url=request.video_url,
            caption=request.caption,
            cover_url=request.cover_url,
            share_to_feed=request.share_to_feed,
        )
        
        logger.info(f"Successfully published Instagram reel: {result.platform_post_id}")
        return result
    
    except Exception as e:
        logger.error(f"Failed to publish Instagram reel: {e}", exc_info=True)
        raise


@router.post("/comments/list", response_model=List[Comment])
def get_comments(
    request: GetCommentsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Comment]:
    """
    Fetch comments for an Instagram post.
    
    Returns:
    - Top-level comments with nested replies
    - Comment text, username, timestamp, like count
    - Hidden status for moderation
    """
    logger.info(f"Fetching comments for Instagram post {request.post_id}")
    
    instagram = get_instagram_platform(
        social_account_id=request.social_account_id,
        current_user=current_user,
        db=db,
    )
    
    try:
        comments = instagram.get_comments(
            post_id=request.post_id,
            limit=request.limit,
        )
        
        logger.info(f"Fetched {len(comments)} comments for post {request.post_id}")
        return comments
    
    except Exception as e:
        logger.error(f"Failed to fetch comments: {e}", exc_info=True)
        raise


@router.post("/comments/reply", response_model=Comment)
def reply_to_comment(
    request: ReplyToCommentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Comment:
    """
    Reply to an Instagram comment.
    
    Requirements:
    - Reply text max: 500 characters
    - Rate limit: 60 replies per hour
    """
    logger.info(f"Replying to Instagram comment {request.comment_id}")
    
    instagram = get_instagram_platform(
        social_account_id=request.social_account_id,
        current_user=current_user,
        db=db,
    )
    
    try:
        reply = instagram.reply_to_comment(
            comment_id=request.comment_id,
            text=request.text,
        )
        
        logger.info(f"Successfully replied to comment: {reply.id}")
        return reply
    
    except Exception as e:
        logger.error(f"Failed to reply to comment: {e}", exc_info=True)
        raise


@router.post("/comments/hide")
def hide_comment(
    request: HideCommentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Hide an Instagram comment.
    
    Hidden comments are only visible to the commenter and their followers.
    Useful for content moderation without deleting.
    """
    logger.info(f"Hiding Instagram comment {request.comment_id}")
    
    instagram = get_instagram_platform(
        social_account_id=request.social_account_id,
        current_user=current_user,
        db=db,
    )
    
    try:
        success = instagram.hide_comment(comment_id=request.comment_id)
        
        if success:
            logger.info(f"Successfully hid comment {request.comment_id}")
            return {"success": True, "comment_id": request.comment_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to hide comment"
            )
    
    except Exception as e:
        logger.error(f"Failed to hide comment: {e}", exc_info=True)
        raise


@router.post("/comments/delete")
def delete_comment(
    request: DeleteCommentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete an Instagram comment.
    
    Permanently removes the comment. Cannot be undone.
    Only works for comments on your own posts or replies you made.
    """
    logger.info(f"Deleting Instagram comment {request.comment_id}")
    
    instagram = get_instagram_platform(
        social_account_id=request.social_account_id,
        current_user=current_user,
        db=db,
    )
    
    try:
        success = instagram.delete_comment(comment_id=request.comment_id)
        
        if success:
            logger.info(f"Successfully deleted comment {request.comment_id}")
            return {"success": True, "comment_id": request.comment_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete comment"
            )
    
    except Exception as e:
        logger.error(f"Failed to delete comment: {e}", exc_info=True)
        raise


@router.post("/analytics", response_model=PostAnalytics)
def get_analytics(
    request: GetAnalyticsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostAnalytics:
    """
    Get analytics/insights for an Instagram post.
    
    Returns:
    - Impressions, reach, likes, comments, saves
    - Engagement rate calculated from metrics
    - Timestamp of data fetch
    
    Note: Insights require Instagram Business/Creator account.
    Personal accounts will only return like/comment counts.
    """
    logger.info(f"Fetching analytics for Instagram post {request.post_id}")
    
    instagram = get_instagram_platform(
        social_account_id=request.social_account_id,
        current_user=current_user,
        db=db,
    )
    
    try:
        analytics = instagram.get_analytics(post_id=request.post_id)
        
        logger.info(f"Fetched analytics for post {request.post_id}: {analytics.likes} likes, {analytics.reach} reach")
        return analytics
    
    except Exception as e:
        logger.error(f"Failed to fetch analytics: {e}", exc_info=True)
        raise


@router.get("/rate-limits")
def get_rate_limits(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get Instagram API rate limits and daily quotas.
    
    Returns current limits (as of 2024):
    - Graph API: 200 calls/hour/user
    - Content Publishing: 25 posts/day/user
    - Comments: 60 calls/hour/user
    """
    return {
        "graph_api": {
            "calls_per_hour": 200,
            "window": "per user",
        },
        "content_publishing": {
            "posts_per_day": 25,
            "includes": ["photos", "reels", "carousels"],
            "window": "rolling 24 hours",
        },
        "comments": {
            "calls_per_hour": 60,
            "includes": ["fetch", "reply", "hide", "delete"],
            "window": "per user",
        },
        "note": "Limits are enforced by Instagram. Monitor responses for rate limit errors.",
    }
