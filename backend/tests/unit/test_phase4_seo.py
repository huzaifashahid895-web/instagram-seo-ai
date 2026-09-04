# backend/tests/unit/test_phase4_seo.py
"""
Unit tests for Phase 4 SEO scoring, keywords, and hashtags.
Tests deterministic scoring logic without requiring external services.
"""

import pytest
from app.services.seo.scoring import SEOScoringService, CaptionAnalysis
from app.services.seo.keywords import KeywordService, KeywordAnalysis
from app.services.seo.hashtags import HashtagService, HashtagAnalysis


# Mock providers for testing
class MockLLMProvider:
    """Mock LLM that returns predictable responses."""
    
    def generate(self, prompt: str, **kwargs) -> str:
        if "keywords" in prompt.lower():
            return """Instagram growth tips
social media marketing
content strategy
engagement tactics
follower growth hacks"""
        elif "hashtags" in prompt.lower():
            return """InstagramGrowth
SocialMediaMarketing
ContentStrategy
EngagementTips
FollowerGrowth"""
        elif "hook" in prompt.lower():
            return "Hook looks attention-grabbing and relevant."
        return "Test response"
    
    def structured_output(self, prompt: str, schema, **kwargs):
        # Return mock HookRubric
        from app.services.seo.scoring import HookRubric
        return HookRubric(
            attention_score=8,
            curiosity_score=7,
            relevance_score=9,
            clarity_score=8,
            overall_score=8,
            reasoning="Strong hook with clear value proposition"
        )


class MockEmbeddingProvider:
    """Mock embeddings that return predictable vectors."""
    
    def embed_text(self, text: str) -> list[float]:
        # Return simple vector based on text length
        base = [0.1] * 384
        base[0] = len(text) / 1000.0  # Vary first dimension
        return base
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


class MockVectorStore:
    """Mock vector store for testing."""
    
    def search(self, query_embedding, n_results=10, where=None):
        # Return mock results (no similar content found)
        return {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": []
        }


# Test Caption Quality Analysis

def test_caption_quality_optimal_length():
    """Test caption quality scoring for optimal length."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    caption = "🌟 Check out this amazing content! 🚀\n\nClick the link in bio to learn more.\n\n#awesome #content"
    analysis = service.score_caption_quality(caption)
    
    assert isinstance(analysis, CaptionAnalysis)
    assert 100 <= analysis.length <= 500  # Optimal range
    assert analysis.has_cta is True  # "Click" detected
    assert analysis.has_emoji is True  # Emojis present
    assert analysis.has_line_breaks is True
    assert 0.0 <= analysis.quality_score <= 1.0
    assert analysis.quality_score > 0.5  # Should score well


def test_caption_quality_too_short():
    """Test caption quality for too-short caption."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    caption = "Short post"
    analysis = service.score_caption_quality(caption)
    
    assert analysis.length < 100
    assert analysis.has_cta is False
    assert analysis.quality_score < 0.5  # Should score lower


def test_caption_quality_no_cta():
    """Test caption without call-to-action."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    caption = "Just sharing my thoughts on this beautiful day. The weather is amazing and I'm feeling grateful."
    analysis = service.score_caption_quality(caption)
    
    assert analysis.has_cta is False
    # Quality should be lower without CTA
    
    caption_with_cta = caption + " Follow for more updates!"
    analysis_with_cta = service.score_caption_quality(caption_with_cta)
    
    assert analysis_with_cta.has_cta is True
    assert analysis_with_cta.quality_score > analysis.quality_score


# Test Hook Strength Scoring

def test_hook_strength_with_llm():
    """Test hook strength scoring using LLM."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    hook = "Want to 10x your Instagram growth in 30 days?"
    score = service.score_hook_strength(hook)
    
    assert 0.0 <= score <= 1.0
    # Mock returns overall_score=8, so normalized = 0.8
    assert score == 0.8


def test_hook_strength_fallback():
    """Test hook strength fallback when LLM fails."""
    
    class FailingLLM:
        def structured_output(self, *args, **kwargs):
            raise Exception("LLM failed")
    
    service = SEOScoringService(
        FailingLLM(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    # Hook with question and number
    hook = "5 secrets to boost engagement?"
    score = service.score_hook_strength(hook)
    
    assert 0.0 <= score <= 1.0
    assert score >= 0.7  # Has question + number


# Test Topic Relevance

def test_topic_relevance_with_pillars():
    """Test topic relevance scoring against brand pillars."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    content = "Instagram marketing tips for small businesses"
    pillars = [
        "Social media marketing strategies",
        "Small business growth",
        "Digital marketing tips"
    ]
    
    score = service.score_topic_relevance(content, pillars)
    
    assert 0.0 <= score <= 1.0
    # Should have decent relevance with embedding similarity


def test_topic_relevance_no_pillars():
    """Test topic relevance with no brand pillars."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    score = service.score_topic_relevance("Any content", None)
    
    assert score == 0.5  # Neutral score


# Test Content Freshness

def test_content_freshness_fresh():
    """Test freshness scoring for fresh content."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()  # Returns no similar content
    )
    
    score = service.score_content_freshness("Completely new and unique content")
    
    assert score == 1.0  # Perfectly fresh


def test_content_freshness_duplicate():
    """Test freshness scoring for duplicate content."""
    
    class DuplicateVectorStore:
        def search(self, query_embedding, n_results=10, where=None):
            # Return very similar content (distance = 0.05)
            return {
                "ids": ["id1"],
                "documents": ["Similar content"],
                "metadatas": [{}],
                "distances": [0.05]  # Very close = high similarity
            }
    
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        DuplicateVectorStore()
    )
    
    score = service.score_content_freshness("Similar content")
    
    assert 0.0 <= score <= 1.0
    assert score < 0.5  # Should penalize duplicates


# Test Complete SEO Score

def test_compute_seo_score_complete():
    """Test complete SEO score computation."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    caption = """🚀 Want to 10x your Instagram growth?

Here are 5 proven strategies that actually work.

Click the link in bio to get the full guide!

#InstagramGrowth #SocialMediaTips"""
    
    score = service.compute_seo_score(
        caption=caption,
        brand_pillars=["Instagram marketing", "Social media growth"],
        target_audience="Small business owners looking to grow on Instagram"
    )
    
    assert 0.0 <= score.overall_score <= 100.0
    assert 0.0 <= score.topic_relevance <= 1.0
    assert 0.0 <= score.hook_strength <= 1.0
    assert 0.0 <= score.caption_quality <= 1.0
    assert 0.0 <= score.content_freshness <= 1.0
    
    # Verify weights sum to 1.0
    weight_sum = sum(score.weights.values())
    assert abs(weight_sum - 1.0) < 0.01  # Allow small float precision error
    
    # Details should be populated
    assert "caption_analysis" in score.details
    assert "hook_strength_raw" in score.details


# Test Keyword Service

def test_generate_keywords():
    """Test keyword generation."""
    service = KeywordService(MockLLMProvider(), MockEmbeddingProvider())
    
    keywords = service.generate_keywords(
        topic="Instagram growth tips",
        num_keywords=5
    )
    
    assert len(keywords) <= 5
    for kw in keywords:
        assert 0.0 <= kw.relevance_score <= 1.0
        assert kw.competition in ["low", "medium", "high"]
        assert kw.suggested_by == "llm"


def test_analyze_keyword_usage():
    """Test keyword usage analysis."""
    service = KeywordService(MockLLMProvider(), MockEmbeddingProvider())
    
    content = "Learn Instagram marketing and social media growth strategies"
    target_keywords = ["Instagram marketing", "social media", "engagement"]
    
    analysis = service.analyze_keyword_usage(content, target_keywords)
    
    assert isinstance(analysis, KeywordAnalysis)
    assert analysis.target_keywords == target_keywords
    assert "Instagram marketing" in analysis.found_keywords
    assert "social media" in analysis.found_keywords
    assert "engagement" in analysis.missing_keywords
    assert 0.0 <= analysis.relevance_score <= 1.0


# Test Hashtag Service

def test_generate_hashtags():
    """Test hashtag generation."""
    service = HashtagService(MockLLMProvider())
    
    hashtags = service.generate_hashtags(
        topic="Instagram growth tips",
        num_hashtags=5
    )
    
    assert len(hashtags) <= 5
    for tag in hashtags:
        assert not tag.hashtag.startswith('#')  # Should be cleaned
        assert tag.category in ["trending", "niche", "community", "branded"]
        assert tag.estimated_reach in ["small", "medium", "large"]
        assert 0.0 <= tag.relevance_score <= 1.0


def test_analyze_hashtag_usage_optimal():
    """Test hashtag analysis for optimal usage."""
    service = HashtagService(MockLLMProvider())
    
    hashtags = ["InstagramGrowth", "SocialMedia", "ContentMarketing", "Engagement"]
    analysis = service.analyze_hashtag_usage(hashtags, platform="instagram")
    
    assert isinstance(analysis, HashtagAnalysis)
    assert analysis.total_hashtags == 4
    assert 3 <= analysis.recommended_count <= 5  # Instagram recommendation
    assert 0.0 <= analysis.quality_score <= 1.0
    assert len(analysis.suggestions) > 0


def test_analyze_hashtag_usage_too_few():
    """Test hashtag analysis with too few hashtags."""
    service = HashtagService(MockLLMProvider())
    
    hashtags = ["OnlyOne"]
    analysis = service.analyze_hashtag_usage(hashtags)
    
    assert analysis.total_hashtags == 1
    assert analysis.quality_score < 0.5
    assert any("Add" in s for s in analysis.suggestions)


def test_analyze_hashtag_usage_too_many():
    """Test hashtag analysis with too many hashtags."""
    service = HashtagService(MockLLMProvider())
    
    hashtags = [f"Tag{i}" for i in range(20)]  # Way too many
    analysis = service.analyze_hashtag_usage(hashtags)
    
    assert analysis.total_hashtags == 20
    assert any("reducing" in s.lower() for s in analysis.suggestions)


# Test integration scenarios

def test_seo_score_with_custom_weights():
    """Test SEO scoring with custom weights."""
    service = SEOScoringService(
        MockLLMProvider(),
        MockEmbeddingProvider(),
        MockVectorStore()
    )
    
    custom_weights = {
        "topic_relevance": 0.30,
        "keyword_relevance": 0.05,
        "hook_strength": 0.30,
        "audience_relevance": 0.10,
        "caption_quality": 0.20,
        "hashtag_quality": 0.05,
        "content_freshness": 0.00
    }
    
    score = service.compute_seo_score(
        caption="Test caption with call to action. Follow me!",
        weights=custom_weights
    )
    
    assert score.weights == custom_weights
    assert 0.0 <= score.overall_score <= 100.0


def test_keyword_service_fallback():
    """Test keyword service fallback when LLM fails."""
    
    class FailingLLM:
        def generate(self, *args, **kwargs):
            raise Exception("LLM failed")
    
    service = KeywordService(FailingLLM(), MockEmbeddingProvider())
    
    keywords = service.generate_keywords("Test topic")
    
    # Should return fallback keyword
    assert len(keywords) >= 1
    assert keywords[0].suggested_by == "fallback"


def test_hashtag_service_fallback():
    """Test hashtag service fallback when LLM fails."""
    
    class FailingLLM:
        def generate(self, *args, **kwargs):
            raise Exception("LLM failed")
    
    service = HashtagService(FailingLLM())
    
    hashtags = service.generate_hashtags("Test topic")
    
    # Should return fallback hashtag
    assert len(hashtags) >= 1
    assert hashtags[0].suggested_by == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
