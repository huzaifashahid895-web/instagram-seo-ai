# backend/tests/unit/test_phase8_comments.py — Phase 8 comment management tests
# Cost classification: FREE + OPEN SOURCE

"""
Test suite for Phase 8: Comment Management System

Tests:
1. Comment classification (rule-based + LLM fallback)
2. Response generation (template-based + brand voice)
3. Comment manager workflow (webhook → classify → respond → approve)
4. Webhook signature validation
5. Escalation logic
"""

import pytest
import uuid
import hmac
import hashlib
import json
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.comment_classifier import (
    CommentClassification,
    ClassificationResult,
    RuleBasedClassifier,
    LLMLessCommentClassifier
)
from app.services.comment_responder import CommentResponder, ResponseTemplate
from app.services.comment_manager import (
    CommentManager,
    WebhookSignatureValidator,
    WebhookPayload,
    CommentResult
)


# ============================================================================
# Comment Classifier Tests
# ============================================================================

class TestRuleBasedClassifier:
    """Test rule-based comment classification."""
    
    def test_classify_spam_with_urls(self):
        """Test spam detection with multiple URLs."""
        classifier = RuleBasedClassifier()
        text = "Check out http://spam.com and https://scam.net for deals!!!"
        result = classifier.classify(text)
        
        assert result.classification == CommentClassification.SPAM
        assert result.confidence > 0.8
        assert "multiple URLs" in result.reasoning.lower()
    
    def test_classify_spam_with_repeated_chars(self):
        """Test spam detection with excessive repeated characters."""
        classifier = RuleBasedClassifier()
        text = "WOWWWW!!!! AMAZINGGGG!!!! CHECKKK THISSS OUTTTT!!!!"
        result = classifier.classify(text)
        
        assert result.classification == CommentClassification.SPAM
        assert result.confidence > 0.7
    
    def test_classify_troll_comment(self):
        """Test troll comment detection."""
        classifier = RuleBasedClassifier()
        text = "You're such a loser, this is garbage"
        result = classifier.classify(text)
        
        assert result.classification == CommentClassification.TROLL
        assert result.confidence > 0.7
    
    def test_classify_question(self):
        """Test question detection."""
        classifier = RuleBasedClassifier()
        text = "How much does this cost?"
        result = classifier.classify(text)
        
        assert result.classification == CommentClassification.QUESTION
        assert result.confidence > 0.7
    
    def test_classify_praise(self):
        """Test praise detection."""
        classifier = RuleBasedClassifier()
        text = "This is absolutely amazing! Love it so much!"
        result = classifier.classify(text)
        
        assert result.classification == CommentClassification.PRAISE
        assert result.confidence > 0.6
    
    def test_classify_negative_feedback(self):
        """Test negative feedback detection."""
        classifier = RuleBasedClassifier()
        text = "I'm disappointed with this product, terrible quality"
        result = classifier.classify(text)
        
        assert result.classification == CommentClassification.NEGATIVE
        assert result.confidence > 0.6
    
    def test_classify_emoji_only(self):
        """Test emoji-only comment classification."""
        classifier = RuleBasedClassifier()
        text = "😍❤️🔥"
        result = classifier.classify(text)
        
        assert result.classification == CommentClassification.POSITIVE
        assert result.confidence > 0.8
    
    def test_classify_unknown_when_no_match(self):
        """Test unknown classification for ambiguous text."""
        classifier = RuleBasedClassifier()
        text = "The weather is nice today"
        result = classifier.classify(text)
        
        assert result.classification == CommentClassification.UNKNOWN
        assert result.confidence < 0.5


class TestLLMLessCommentClassifier:
    """Test LLM-less comment classifier with optional LLM fallback."""
    
    @pytest.mark.asyncio
    async def test_classify_with_rules_only(self):
        """Test classification using rules without LLM."""
        classifier = LLMLessCommentClassifier(llm_provider=None)
        text = "How can I order this?"
        
        result = await classifier.classify(text)
        
        assert result.classification == CommentClassification.QUESTION
        assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_classify_with_llm_fallback(self):
        """Test LLM fallback for ambiguous comments."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "SUPPORT"
        
        classifier = LLMLessCommentClassifier(llm_provider=mock_llm)
        text = "I need help with something"
        
        result = await classifier.classify(text, use_llm_fallback=True)
        
        assert result.classification == CommentClassification.SUPPORT
        mock_llm.generate.assert_called_once()


# ============================================================================
# Comment Responder Tests
# ============================================================================

class TestCommentResponder:
    """Test comment response generation."""
    
    @pytest.mark.asyncio
    async def test_generate_response_for_praise(self):
        """Test response generation for praise comments."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Thank you so much! We're thrilled you love it! 💕"
        
        responder = CommentResponder(llm_provider=mock_llm)
        
        mock_comment = MagicMock()
        mock_comment.text = "This is amazing!"
        mock_comment.classification = CommentClassification.PRAISE
        
        response = await responder.generate_response(
            comment=mock_comment,
            brand_name="TestBrand"
        )
        
        assert response is not None
        assert len(response) > 0
        mock_llm.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_for_question(self):
        """Test response generation for product questions."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Great question! This product costs $29.99. DM us for more details!"
        
        responder = CommentResponder(llm_provider=mock_llm)
        
        mock_comment = MagicMock()
        mock_comment.text = "How much does this cost?"
        mock_comment.classification = CommentClassification.PRODUCT_QUESTION
        
        response = await responder.generate_response(
            comment=mock_comment,
            brand_name="TestBrand"
        )
        
        assert response is not None
        assert len(response) > 10
    
    @pytest.mark.asyncio
    async def test_no_response_for_spam(self):
        """Test that spam comments don't get responses."""
        mock_llm = AsyncMock()
        responder = CommentResponder(llm_provider=mock_llm)
        
        mock_comment = MagicMock()
        mock_comment.text = "http://spam.com CHECK THIS OUT!!!"
        mock_comment.classification = CommentClassification.SPAM
        
        response = await responder.generate_response(
            comment=mock_comment,
            brand_name="TestBrand"
        )
        
        # Should return None or empty response for spam
        assert response is None or response == ""
        mock_llm.generate.assert_not_called()


# ============================================================================
# Webhook Signature Validation Tests
# ============================================================================

class TestWebhookSignatureValidator:
    """Test Instagram webhook signature validation."""
    
    def test_validate_signature_success(self):
        """Test successful signature validation."""
        app_secret = "test_secret_key"
        validator = WebhookSignatureValidator(app_secret=app_secret)
        
        payload = '{"entry": [{"id": "123"}]}'
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        signature_header = f"sha1={expected_signature}"
        
        result = validator.validate(signature_header, payload)
        assert result is True
    
    def test_validate_signature_failure(self):
        """Test signature validation failure with wrong secret."""
        validator = WebhookSignatureValidator(app_secret="correct_secret")
        
        payload = '{"entry": [{"id": "123"}]}'
        wrong_signature = hmac.new(
            b"wrong_secret",
            payload.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        signature_header = f"sha1={wrong_signature}"
        
        result = validator.validate(signature_header, payload)
        assert result is False
    
    def test_validate_signature_malformed_header(self):
        """Test validation with malformed signature header."""
        validator = WebhookSignatureValidator(app_secret="test_secret")
        
        result = validator.validate("invalid_format", '{"data": "test"}')
        assert result is False
    
    def test_validate_signature_missing_sha1_prefix(self):
        """Test validation with missing sha1= prefix."""
        validator = WebhookSignatureValidator(app_secret="test_secret")
        
        result = validator.validate("abc123def456", '{"data": "test"}')
        assert result is False


# ============================================================================
# Comment Manager Tests
# ============================================================================

class TestCommentManager:
    """Test comment management workflow."""
    
    @pytest.mark.asyncio
    async def test_handle_webhook_success(self):
        """Test successful webhook processing."""
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = ClassificationResult(
            classification=CommentClassification.POSITIVE,
            confidence=0.9,
            reasoning="Positive sentiment detected"
        )
        
        mock_responder = AsyncMock()
        mock_responder.generate_response.return_value = "Thank you! 💕"
        
        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        
        manager = CommentManager(
            classifier=mock_classifier,
            responder=mock_responder,
            validator=mock_validator
        )
        
        payload = {
            "entry": [{
                "id": "instagram_account_id",
                "changes": [{
                    "field": "comments",
                    "value": {
                        "id": "comment_123",
                        "text": "Love this!",
                        "from": {"id": "user_456", "username": "testuser"},
                        "media": {"id": "media_789"}
                    }
                }]
            }]
        }
        
        signature = "sha1=valid_signature"
        
        # Mock the async session and database operations
        with patch('app.services.comment_manager.AsyncSession') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            result = await manager.handle_webhook(
                payload=payload,
                signature=signature,
                db=mock_db
            )
        
        assert result is not None
        mock_classifier.classify.assert_called_once()
        mock_responder.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_escalate_sensitive_comment(self):
        """Test escalation of sensitive comments."""
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = ClassificationResult(
            classification=CommentClassification.SENSITIVE,
            confidence=0.85,
            reasoning="Contains sensitive content"
        )
        
        manager = CommentManager(classifier=mock_classifier)
        
        mock_comment = MagicMock()
        mock_comment.text = "I have a serious complaint about privacy"
        mock_comment.id = uuid.uuid4()
        
        # Mock database session
        mock_db = AsyncMock()
        
        result = await manager._process_comment(mock_comment, mock_db)
        
        # Sensitive comments should be escalated
        assert result.requires_approval is True
        assert result.escalated is True
    
    @pytest.mark.asyncio
    async def test_no_response_for_troll(self):
        """Test that troll comments don't get automated responses."""
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = ClassificationResult(
            classification=CommentClassification.TROLL,
            confidence=0.9,
            reasoning="Troll pattern detected"
        )
        
        mock_responder = AsyncMock()
        
        manager = CommentManager(
            classifier=mock_classifier,
            responder=mock_responder
        )
        
        mock_comment = MagicMock()
        mock_comment.text = "You're terrible"
        mock_comment.id = uuid.uuid4()
        
        mock_db = AsyncMock()
        
        result = await manager._process_comment(mock_comment, mock_db)
        
        # Troll comments should not get responses
        assert result.response_draft_id is None
        mock_responder.generate_response.assert_not_called()


# ============================================================================
# Integration Tests
# ============================================================================

class TestCommentManagementIntegration:
    """Integration tests for end-to-end comment workflow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_positive_comment_flow(self):
        """Test complete flow from webhook to response generation."""
        # Setup
        classifier = LLMLessCommentClassifier(llm_provider=None)
        
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Thank you so much! We appreciate your support! 💕"
        
        responder = CommentResponder(llm_provider=mock_llm)
        
        validator = WebhookSignatureValidator(app_secret="test_secret")
        
        manager = CommentManager(
            classifier=classifier,
            responder=responder,
            validator=validator
        )
        
        # Test data
        comment_text = "This is absolutely amazing! Love it! ❤️"
        
        # Classify
        classification_result = await classifier.classify(comment_text)
        assert classification_result.classification == CommentClassification.PRAISE
        
        # Generate response
        mock_comment = MagicMock()
        mock_comment.text = comment_text
        mock_comment.classification = classification_result.classification
        
        response = await responder.generate_response(
            comment=mock_comment,
            brand_name="TestBrand"
        )
        
        assert response is not None
        assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_end_to_end_question_flow(self):
        """Test complete flow for question handling."""
        classifier = LLMLessCommentClassifier(llm_provider=None)
        
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Great question! Please DM us and we'll be happy to help! 😊"
        
        responder = CommentResponder(llm_provider=mock_llm)
        
        comment_text = "How much does this cost and where can I buy it?"
        
        # Classify
        classification_result = await classifier.classify(comment_text)
        assert classification_result.classification == CommentClassification.QUESTION
        
        # Generate response
        mock_comment = MagicMock()
        mock_comment.text = comment_text
        mock_comment.classification = classification_result.classification
        
        response = await responder.generate_response(
            comment=mock_comment,
            brand_name="TestBrand"
        )
        
        assert response is not None
        assert len(response) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
