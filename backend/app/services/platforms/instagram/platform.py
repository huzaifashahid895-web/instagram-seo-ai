# backend/app/services/platforms/instagram/platform.py
# Cost classification: FREE, REQUIRES INTERNET
"""
Instagram platform service implementing SocialPlatform protocol.

Provides publishing, comment management, and analytics collection
via the Instagram Graph API.

Rate Limits (as of 2024, verify current limits):
- Graph API: 200 calls per hour per user
- Content Publishing API: 25 posts per day per user (Reels count as 1)
- Comments: 60 calls per hour per user

Official docs: https://developers.facebook.com/docs/instagram-api
"""

import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.config import settings
from app.services.providers import PublishResult, Comment, PostAnalytics

logger = logging.getLogger(__name__)

# Instagram Graph API base URLs
GRAPH_API_VERSION = "v18.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class InstagramPlatform:
    """
    Instagram platform integration implementing SocialPlatform protocol.
    
    Handles:
    - Publishing posts, reels, carousels, stories
    - Comment management (fetch, reply, hide)
    - Analytics/insights collection
    - Rate limiting awareness
    """
    
    def __init__(self, access_token: str, instagram_user_id: str):
        """
        Initialize Instagram platform service.
        
        Args:
            access_token: Instagram long-lived access token
            instagram_user_id: Instagram Business/Creator account ID
        """
        self.access_token = access_token
        self.user_id = instagram_user_id
        self._last_request_time = 0.0
        self._min_request_interval = 0.5  # 500ms between requests
    
    def _rate_limit_wait(self):
        """Enforce minimum time between API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make authenticated request to Instagram Graph API.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint (e.g., "/me/media")
            params: Query parameters
            data: Request body (for POST)
            
        Returns:
            JSON response as dict
            
        Raises:
            HTTPException: On API errors
        """
        self._rate_limit_wait()
        
        url = f"{GRAPH_BASE_URL}{endpoint}"
        
        # Add access token to params
        if params is None:
            params = {}
        params["access_token"] = self.access_token
        
        # Build request
        if method == "GET":
            url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            request = urllib.request.Request(url_with_params, method="GET")
        
        elif method == "POST":
            url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            body = json.dumps(data or {}).encode("utf-8") if data else None
            request = urllib.request.Request(url_with_params, data=body, method="POST")
            if body:
                request.add_header("Content-Type", "application/json")
        
        elif method == "DELETE":
            url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            request = urllib.request.Request(url_with_params, method="DELETE")
        
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Execute request
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            logger.error(f"Instagram API error: {exc.code} {error_body}")
            
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
            except json.JSONDecodeError:
                error_msg = error_body
            
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Instagram API error: {error_msg}"
            ) from exc
        
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.error(f"Instagram API request failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Instagram API request failed"
            ) from exc
    
    def publish_post(
        self,
        image_url: str,
        caption: str | None = None,
        location_id: str | None = None,
        user_tags: list[dict] | None = None,
    ) -> PublishResult:
        """
        Publish a single image post to Instagram.
        
        Args:
            image_url: Public URL to the image (must be accessible to Instagram)
            caption: Post caption (max 2200 chars)
            location_id: Facebook Page ID for location tagging
            user_tags: List of user tags [{"username": "user", "x": 0.5, "y": 0.5}, ...]
            
        Returns:
            PublishResult with Instagram post ID and permalink
        """
        logger.info(f"Publishing post to Instagram for user {self.user_id}")
        
        # Step 1: Create media container
        container_params = {
            "image_url": image_url,
        }
        if caption:
            container_params["caption"] = caption[:2200]  # Instagram limit
        if location_id:
            container_params["location_id"] = location_id
        if user_tags:
            container_params["user_tags"] = json.dumps(user_tags)
        
        container_response = self._make_request(
            "POST",
            f"/{self.user_id}/media",
            params=container_params,
        )
        
        container_id = container_response.get("id")
        if not container_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Instagram did not return a container ID"
            )
        
        # Step 2: Publish the container
        publish_response = self._make_request(
            "POST",
            f"/{self.user_id}/media_publish",
            params={"creation_id": container_id},
        )
        
        post_id = publish_response.get("id")
        if not post_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Instagram publish failed"
            )
        
        # Step 3: Get permalink
        post_data = self._make_request(
            "GET",
            f"/{post_id}",
            params={"fields": "permalink,timestamp"},
        )
        
        logger.info(f"Successfully published Instagram post: {post_id}")
        
        return PublishResult(
            platform_post_id=post_id,
            permalink=post_data.get("permalink"),
            published_at=post_data.get("timestamp"),
            status="published",
        )
    
    def publish_video(
        self,
        video_url: str,
        caption: str | None = None,
        cover_url: str | None = None,
        share_to_feed: bool = True,
    ) -> PublishResult:
        """
        Publish a video (Reel) to Instagram.
        
        Args:
            video_url: Public URL to the video (must be accessible to Instagram)
            caption: Reel caption (max 2200 chars)
            cover_url: Optional custom cover image URL
            share_to_feed: Whether to share Reel to main feed
            
        Returns:
            PublishResult with Instagram reel ID and permalink
        """
        logger.info(f"Publishing reel to Instagram for user {self.user_id}")
        
        # Step 1: Create reel container
        container_params = {
            "media_type": "REELS",
            "video_url": video_url,
            "share_to_feed": str(share_to_feed).lower(),
        }
        if caption:
            container_params["caption"] = caption[:2200]
        if cover_url:
            container_params["cover_url"] = cover_url
        
        container_response = self._make_request(
            "POST",
            f"/{self.user_id}/media",
            params=container_params,
        )
        
        container_id = container_response.get("id")
        if not container_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Instagram did not return a container ID for reel"
            )
        
        # Step 2: Poll for container status (video processing can take time)
        max_attempts = 60  # 5 minutes max
        for attempt in range(max_attempts):
            status_response = self._make_request(
                "GET",
                f"/{container_id}",
                params={"fields": "status_code"},
            )
            
            status_code = status_response.get("status_code")
            
            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Instagram video processing failed"
                )
            elif status_code in ["IN_PROGRESS", "PUBLISHED"]:
                time.sleep(5)  # Wait 5 seconds before next check
                continue
            else:
                logger.warning(f"Unknown Instagram status_code: {status_code}")
                time.sleep(5)
        
        # Step 3: Publish the reel
        publish_response = self._make_request(
            "POST",
            f"/{self.user_id}/media_publish",
            params={"creation_id": container_id},
        )
        
        reel_id = publish_response.get("id")
        if not reel_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Instagram reel publish failed"
            )
        
        # Step 4: Get permalink
        reel_data = self._make_request(
            "GET",
            f"/{reel_id}",
            params={"fields": "permalink,timestamp"},
        )
        
        logger.info(f"Successfully published Instagram reel: {reel_id}")
        
        return PublishResult(
            platform_post_id=reel_id,
            permalink=reel_data.get("permalink"),
            published_at=reel_data.get("timestamp"),
            status="published",
        )
    
    def get_comments(
        self,
        post_id: str,
        limit: int = 50,
    ) -> list[Comment]:
        """
        Fetch comments for a post.
        
        Args:
            post_id: Instagram media ID
            limit: Maximum number of comments to fetch
            
        Returns:
            List of Comment objects
        """
        logger.info(f"Fetching comments for post {post_id}")
        
        response = self._make_request(
            "GET",
            f"/{post_id}/comments",
            params={
                "fields": "id,text,username,timestamp,like_count,hidden,replies{id,text,username,timestamp}",
                "limit": str(min(limit, 50)),  # Instagram max is 50
            },
        )
        
        comments = []
        for comment_data in response.get("data", []):
            replies = []
            for reply_data in comment_data.get("replies", {}).get("data", []):
                replies.append(Comment(
                    id=reply_data["id"],
                    post_id=post_id,
                    text=reply_data.get("text", ""),
                    username=reply_data.get("username", ""),
                    timestamp=reply_data.get("timestamp"),
                ))
            
            comments.append(Comment(
                id=comment_data["id"],
                post_id=post_id,
                text=comment_data.get("text", ""),
                username=comment_data.get("username", ""),
                timestamp=comment_data.get("timestamp"),
                like_count=comment_data.get("like_count", 0),
                is_hidden=comment_data.get("hidden", False),
                replies=replies,
            ))
        
        logger.info(f"Fetched {len(comments)} comments for post {post_id}")
        return comments
    
    def reply_to_comment(
        self,
        comment_id: str,
        text: str,
    ) -> Comment:
        """
        Reply to a comment.
        
        Args:
            comment_id: Instagram comment ID
            text: Reply text (max 500 chars for comments)
            
        Returns:
            Comment object for the reply
        """
        logger.info(f"Replying to comment {comment_id}")
        
        response = self._make_request(
            "POST",
            f"/{comment_id}/replies",
            params={"message": text[:500]},
        )
        
        reply_id = response.get("id")
        if not reply_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Instagram reply failed"
            )
        
        logger.info(f"Successfully replied to comment: {reply_id}")
        
        return Comment(
            id=reply_id,
            post_id="",  # Not returned by API
            text=text,
            username=self.user_id,  # Our reply
            timestamp=datetime.utcnow().isoformat(),
        )
    
    def get_analytics(
        self,
        post_id: str,
    ) -> PostAnalytics:
        """
        Get analytics/insights for a post.
        
        Args:
            post_id: Instagram media ID
            
        Returns:
            PostAnalytics with engagement metrics
        """
        logger.info(f"Fetching analytics for post {post_id}")
        
        # Fetch basic metrics (available for all posts)
        response = self._make_request(
            "GET",
            f"/{post_id}",
            params={
                "fields": "like_count,comments_count,media_type,timestamp",
            },
        )
        
        # Try to fetch insights (requires Instagram Business account)
        impressions = 0
        reach = 0
        saves = 0
        
        try:
            insights_response = self._make_request(
                "GET",
                f"/{post_id}/insights",
                params={
                    "metric": "impressions,reach,saves",
                },
            )
            
            for insight in insights_response.get("data", []):
                metric_name = insight.get("name")
                metric_values = insight.get("values", [])
                
                if metric_values and "value" in metric_values[0]:
                    value = metric_values[0]["value"]
                    
                    if metric_name == "impressions":
                        impressions = value
                    elif metric_name == "reach":
                        reach = value
                    elif metric_name == "saves":
                        saves = value
        
        except HTTPException:
            logger.warning(f"Could not fetch insights for post {post_id} (may require Business account)")
        
        likes = response.get("like_count", 0)
        comments = response.get("comments_count", 0)
        
        # Calculate engagement rate
        engagement = likes + comments + saves
        engagement_rate = (engagement / reach * 100) if reach > 0 else 0.0
        
        logger.info(f"Analytics for post {post_id}: {likes} likes, {comments} comments, {reach} reach")
        
        return PostAnalytics(
            post_id=post_id,
            impressions=impressions,
            reach=reach,
            likes=likes,
            comments=comments,
            shares=0,  # Instagram doesn't expose share counts via API
            saves=saves,
            engagement_rate=round(engagement_rate, 2),
            fetched_at=datetime.utcnow().isoformat(),
        )
    
    def hide_comment(self, comment_id: str) -> bool:
        """
        Hide a comment.
        
        Args:
            comment_id: Instagram comment ID
            
        Returns:
            True if successful
        """
        logger.info(f"Hiding comment {comment_id}")
        
        self._make_request(
            "POST",
            f"/{comment_id}",
            params={"hide": "true"},
        )
        
        logger.info(f"Successfully hid comment {comment_id}")
        return True
    
    def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a comment.
        
        Args:
            comment_id: Instagram comment ID
            
        Returns:
            True if successful
        """
        logger.info(f"Deleting comment {comment_id}")
        
        self._make_request(
            "DELETE",
            f"/{comment_id}",
        )
        
        logger.info(f"Successfully deleted comment {comment_id}")
        return True
