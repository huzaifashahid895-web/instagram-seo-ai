# backend/tests/api/test_webhooks_instagram.py
# Cost classification: FREE + OPEN SOURCE
"""
Integration tests for Instagram webhooks API endpoints.

Tests cover:
- Webhook verification (GET /instagram)
- Event handling (POST /instagram)
- Signature validation
- Comment and mention event processing
"""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestInstagramWebhookVerification:
    """Tests for webhook verification (GET /webhooks/instagram)."""
    
    def test_verification_success(self):
        """Test successful webhook verification."""
        verify_token = "test_verify_token_123"
        
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN = verify_token
            
            response = client.get(
                "/webhooks/instagram",
                params={
                    "hub.mode": "subscribe",
                    "hub.challenge": "test_challenge_12345",
                    "hub.verify_token": verify_token
                }
            )
        
        assert response.status_code == 200
        assert response.text == "test_challenge_12345"
    
    def test_verification_missing_token(self):
        """Test verification without verify_token parameter."""
        response = client.get(
            "/webhooks/instagram",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test_challenge"
            }
        )
        
        assert response.status_code == 403
    
    def test_verification_invalid_token(self):
        """Test verification with wrong verify_token."""
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN = "correct_token"
            
            response = client.get(
                "/webhooks/instagram",
                params={
                    "hub.mode": "subscribe",
                    "hub.challenge": "test_challenge",
                    "hub.verify_token": "wrong_token"
                }
            )
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Verification token mismatch"
    
    def test_verification_invalid_mode(self):
        """Test verification with invalid mode."""
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN = "test_token"
            
            response = client.get(
                "/webhooks/instagram",
                params={
                    "hub.mode": "unsubscribe",
                    "hub.challenge": "test_challenge",
                    "hub.verify_token": "test_token"
                }
            )
        
        assert response.status_code == 403


class TestInstagramWebhookEventHandling:
    """Tests for webhook event handling (POST /webhooks/instagram)."""
    
    def create_signature(self, body: bytes, secret: str) -> str:
        """Create HMAC-SHA256 signature."""
        signature = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def test_comment_event_processed(self):
        """Test that comment events are processed."""
        event_body = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841400000000000",
                    "time": 1704067200,
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "17850000000000000",
                                "text": "Great post!",
                                "from": {
                                    "id": "17840000000000000",
                                    "username": "test_user"
                                },
                                "media": {
                                    "id": "17841400000000000"
                                }
                            }
                        }
                    ]
                }
            ]
        }
        
        body_bytes = json.dumps(event_body).encode("utf-8")
        signature = self.create_signature(body_bytes, "test_secret")
        
        with patch("app.api.webhooks.settings") as mock_settings, \
             patch("app.api.webhooks._handle_comment_event") as mock_handler:
            
            mock_settings.INSTAGRAM_APP_SECRET = "test_secret"
            mock_settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN = ""
            
            response = client.post(
                "/webhooks/instagram",
                content=body_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_handler.assert_called_once()
    
    def test_mention_event_processed(self):
        """Test that mention events are processed."""
        event_body = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841400000000000",
                    "time": 1704067200,
                    "changes": [
                        {
                            "field": "mentions",
                            "value": {
                                "id": "17841400000000000",
                                "caption": "Check this out!",
                                "from": {
                                    "id": "17840000000000000",
                                    "username": "other_user"
                                }
                            }
                        }
                    ]
                }
            ]
        }
        
        body_bytes = json.dumps(event_body).encode("utf-8")
        signature = self.create_signature(body_bytes, "test_secret")
        
        with patch("app.api.webhooks.settings") as mock_settings, \
             patch("app.api.webhooks._handle_mention_event") as mock_handler:
            
            mock_settings.INSTAGRAM_APP_SECRET = "test_secret"
            mock_settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN = ""
            
            response = client.post(
                "/webhooks/instagram",
                content=body_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 200
        mock_handler.assert_called_once()
    
    def test_invalid_signature_rejected(self):
        """Test that invalid signatures are rejected."""
        event_body = {
            "object": "instagram",
            "entry": []
        }
        
        body_bytes = json.dumps(event_body).encode("utf-8")
        
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.INSTAGRAM_APP_SECRET = "test_secret"
            mock_settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN = ""
            
            response = client.post(
                "/webhooks/instagram",
                content=body_bytes,
                headers={
                    "X-Hub-Signature-256": "sha256=invalid_signature",
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid signature"
    
    def test_missing_signature_with_app_secret(self):
        """Test that requests without signature are rejected when secret is set."""
        event_body = {
            "object": "instagram",
            "entry": []
        }
        
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.INSTAGRAM_APP_SECRET = "test_secret"
            
            response = client.post(
                "/webhooks/instagram",
                content=json.dumps(event_body),
                headers={"Content-Type": "application/json"}
            )
        
        assert response.status_code == 403
    
    def test_json_parse_error(self):
        """Test handling of invalid JSON body."""
        response = client.post(
            "/webhooks/instagram",
            content="not valid json",
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=test"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"]
    
    def test_unhandled_field_ignored(self):
        """Test that unhandled fields don't cause errors."""
        event_body = {
            "object": "instagram",
            "entry": [
                {
                    "id": "123",
                    "time": 1234567890,
                    "changes": [
                        {
                            "field": "some_new_field",
                            "value": {}
                        }
                    ]
                }
            ]
        }
        
        body_bytes = json.dumps(event_body).encode("utf-8")
        signature = self.create_signature(body_bytes, "test_secret")
        
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.INSTAGRAM_APP_SECRET = "test_secret"
            
            response = client.post(
                "/webhooks/instagram",
                content=body_bytes,
                headers={
                    "X-Hub-Signature-256": signature
                }
            )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_non_instagram_object_ignored(self):
        """Test that non-instagram objects are ignored."""
        event_body = {
            "object": "page",  # Not instagram
            "entry": []
        }
        
        body_bytes = json.dumps(event_body).encode("utf-8")
        signature = self.create_signature(body_bytes, "test_secret")
        
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.INSTAGRAM_APP_SECRET = "test_secret"
            
            response = client.post(
                "/webhooks/instagram",
                content=body_bytes,
                headers={
                    "X-Hub-Signature-256": signature
                }
            )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"


class TestWebhookHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self):
        """Test webhook health check."""
        response = client.get("/webhooks/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert "webhooks" in data
        assert "instagram" in data["webhooks"]
        assert "setup_instructions" in data


class TestWebhookIntegration:
    """Integration tests requiring real environment setup."""
    
    def test_signature_verification_with_real_secret(self):
        """Test signature verification with actual app secret."""
        # This test requires INSTAGRAM_APP_SECRET to be set
        import os
        
        app_secret = os.environ.get("INSTAGRAM_WEBHOOK_TEST_SECRET")
        if not app_secret:
            pytest.skip("INSTAGRAM_WEBHOOK_TEST_SECRET not set")
        
        event_body = {
            "object": "instagram",
            "entry": []
        }
        
        body_bytes = json.dumps(event_body).encode("utf-8")
        signature = self.create_signature(body_bytes, app_secret)
        
        response = client.post(
            "/webhooks/instagram",
            content=body_bytes,
            headers={
                "X-Hub-Signature-256": signature
            }
        )
        
        assert response.status_code == 200
