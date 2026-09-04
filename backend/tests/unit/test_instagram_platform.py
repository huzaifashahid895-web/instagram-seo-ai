# backend/tests/unit/test_instagram_platform.py
# Cost classification: FREE + OPEN SOURCE
"""
Unit tests for Instagram platform service.

These tests verify the InstagramPlatform class methods work correctly
by mocking the underlying HTTP requests.
"""

import json
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from app.services.platforms.instagram.platform import InstagramPlatform


class TestInstagramPlatformInit:
    """Tests for InstagramPlatform initialization."""
    
    def test_init_with_valid_token(self):
        """Test initialization with valid access token."""
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        assert platform.access_token == "test_token"
        assert platform.user_id == "123456789"
        assert platform._min_request_interval == 0.5  # 500ms default


class TestInstagramPlatformPublishPost:
    """Tests for publish_post method."""
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_publish_post_success(self, mock_urllib):
        """Test successful image post publishing."""
        # Mock responses for the two API calls
        mock_response1 = MagicMock()
        mock_response1.read.return_value = json.dumps({
            "id": "1234567890"
        }).encode("utf-8")
        mock_response1.__enter__.return_value = mock_response1
        mock_response1.__exit__.return_value = None
        
        mock_response2 = MagicMock()
        mock_response2.read.return_value = json.dumps({
            "permalink": "https://instagram.com/p/abc123",
            "timestamp": "2024-01-01T00:00:00Z"
        }).encode("utf-8")
        mock_response2.__enter__.return_value = mock_response2
        mock_response2.__exit__.return_value = None
        
        mock_urllib.request.Request = MagicMock()
        mock_urllib.request.urlopen.return_value = mock_response1
        
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        # The actual implementation uses urllib directly, not a mockable client
        # This test verifies the method structure without making real HTTP calls
        result = platform.publish_post(
            image_url="https://example.com/image.jpg",
            caption="Test caption"
        )
        
        # Verify result structure
        assert result.platform_post_id == "1234567890"
        assert result.status == "published"
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_publish_post_without_caption(self, mock_urllib):
        """Test publishing post without caption."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": "9876543210"
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        
        mock_urllib.request.urlopen.return_value = mock_response
        
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        result = platform.publish_post(
            image_url="https://example.com/image.jpg"
        )
        
        assert result.platform_post_id == "9876543210"


class TestInstagramPlatformPublishVideo:
    """Tests for publish_video method."""
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_publish_video_success(self, mock_urllib):
        """Test successful video reel publishing."""
        # Container creation response
        mock_response1 = MagicMock()
        mock_response1.read.return_value = json.dumps({
            "id": "container_123"
        }).encode("utf-8")
        mock_response1.__enter__.return_value = mock_response1
        mock_response1.__exit__.return_value = None
        
        # Status polling responses
        mock_response2 = MagicMock()
        mock_response2.read.return_value = json.dumps({
            "status_code": "FINISHED"
        }).encode("utf-8")
        mock_response2.__enter__.return_value = mock_response2
        mock_response2.__exit__.return_value = None
        
        # Final reel info response
        mock_response3 = MagicMock()
        mock_response3.read.return_value = json.dumps({
            "id": "reel_456",
            "permalink": "https://instagram.com/reel/abc123",
            "timestamp": "2024-01-01T00:00:00Z"
        }).encode("utf-8")
        mock_response3.__enter__.return_value = mock_response3
        mock_response3.__exit__.return_value = None
        
        mock_urllib.request.urlopen.return_value = mock_response1
        
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        result = platform.publish_video(
            video_url="https://example.com/video.mp4",
            caption="Test reel"
        )
        
        assert result.platform_post_id == "reel_456"
        assert result.status == "published"


class TestInstagramPlatformGetComments:
    """Tests for get_comments method."""
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_get_comments_success(self, mock_urllib):
        """Test fetching comments from a post."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "data": [
                {
                    "id": "comment_1",
                    "text": "Great post!",
                    "username": "user1",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "like_count": 5,
                    "hidden": False,
                    "replies": {
                        "data": [
                            {
                                "id": "reply_1",
                                "text": "Thanks!",
                                "username": "user2",
                                "timestamp": "2024-01-01T00:01:00Z"
                            }
                        ]
                    }
                }
            ]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        
        mock_urllib.request.urlopen.return_value = mock_response
        
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        comments = platform.get_comments(post_id="1234567890", limit=10)
        
        assert len(comments) == 1
        assert comments[0].id == "comment_1"
        assert "Great post!" in comments[0].text
        assert comments[0].username == "user1"
        assert len(comments[0].replies) == 1


class TestInstagramPlatformReplyToComment:
    """Tests for reply_to_comment method."""
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_reply_to_comment_success(self, mock_urllib):
        """Test replying to a comment."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": "reply_789"
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        
        mock_urllib.request.urlopen.return_value = mock_response
        
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        result = platform.reply_to_comment(
            comment_id="comment_1",
            text="Thanks for your feedback!"
        )
        
        assert result.id == "reply_789"


class TestInstagramPlatformDeleteComment:
    """Tests for delete_comment method."""
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_delete_comment_success(self, mock_urllib):
        """Test deleting a comment."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "success": True
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        
        mock_urllib.request.urlopen.return_value = mock_response
        
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        result = platform.delete_comment(comment_id="comment_1")
        
        assert result is True


class TestInstagramPlatformHideComment:
    """Tests for hide_comment method."""
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_hide_comment_success(self, mock_urllib):
        """Test hiding a comment."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "success": True
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        
        mock_urllib.request.urlopen.return_value = mock_response
        
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        result = platform.hide_comment(comment_id="comment_1")
        
        assert result is True


class TestInstagramPlatformGetAnalytics:
    """Tests for get_analytics method."""
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_get_analytics_success(self, mock_urllib):
        """Test fetching post analytics."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "data": [
                {"name": "impressions", "values": [{"value": 1500}]},
                {"name": "reach", "values": [{"value": 800}]},
                {"name": "engagement", "values": [{"value": 45}]},
                {"name": "saved", "values": [{"value": 12}]},
                {"name": "video_views", "values": [{"value": 500}]}
            ]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        
        mock_urllib.request.urlopen.return_value = mock_response
        
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        analytics = platform.get_analytics(post_id="1234567890")
        
        assert analytics is not None
        assert analytics.impressions == 1500
        assert analytics.reach == 800
        assert analytics.engagement == 45
        assert analytics.saved == 12
        assert analytics.video_views == 500


class TestInstagramPlatformRateLimiting:
    """Tests for rate limiting behavior."""
    
    def test_rate_limit_interval(self):
        """Test that rate limit interval is configured correctly."""
        platform = InstagramPlatform(
            access_token="test_token",
            instagram_user_id="123456789"
        )
        
        assert platform._min_request_interval == 0.5  # 500ms


class TestInstagramPlatformErrorHandling:
    """Tests for error handling."""
    
    @patch("app.services.platforms.instagram.platform.urllib")
    def test_http_error_handling(self, mock_urllib):
        """Test that HTTP errors are properly handled."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "error": {
                "message": "Invalid OAuth access token",
                "code": 190
            }
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        
        mock_urllib.request.urlopen.side_effect = Exception("HTTP Error 400")
        
        platform = InstagramPlatform(
            access_token="invalid_token",
            instagram_user_id="123456789"
        )
        
        # Should raise HTTPException for API errors
        try:
            platform.get_comments(post_id="1234567890")
            assert False, "Expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 502
            assert "Instagram API error" in str(e.detail)
