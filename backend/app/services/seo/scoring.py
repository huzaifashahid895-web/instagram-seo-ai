# backend/app/services/seo/scoring.py
# Cost classification: FREE + OPEN SOURCE
"""
SEO scoring engine - deterministic + LLM-based scoring for social media content.
All scores are internal optimization heuristics, not claims about platform algorithms.
"""

import re
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict

from app.services.providers import LLMProvider, EmbeddingProvider
from app.services.vector_store.chroma_store import ChromaVectorStore


class HookRubric(BaseModel):
    """Structured output for hook strength scoring"""
    attention_score: int  # 1-10: Does it grab attention in first 2 seconds?
    curiosity_score: int  # 1-10: Does it create curiosity gap?
    relevance_score: int  # 1-10: Is it relevant to target audience?
    clarity_score: int    # 1-10: Is the value proposition clear?
    overall_score: int    # 1-10: Overall hook strength
    reasoning: str        # Brief explanation


class CaptionAnalysis(BaseModel):
    """Deterministic caption quality metrics"""
    length: int
    has_cta: bool
    has_emoji: bool
    has_line_breaks: bool
    readability_score: float  # Flesch reading ease approximation
    sentence_count: int
    avg_sentence_length: float
    quality_score: float  # 0-1 normalized


class SEOScore(BaseModel):
    """Complete SEO score breakdown"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    overall_score: float  # 0-100
    topic_relevance: float  # 0-1
    keyword_relevance: float  # 0-1
    hook_strength: float  # 0-1
    audience_relevance: float  # 0-1
    caption_quality: float  # 0-1
    hashtag_quality: float  # 0-1
    content_freshness: float  # 0-1
    
    # Weights used
    weights: Dict[str, float]
    
    # Details for debugging/transparency
    details: Dict[str, Any]


class SEOScoringService:
    """
    SEO scoring service combining deterministic and LLM-based scoring.
    
    Design principle: Every score is either:
    - Fully deterministic (embeddings, stats, readability)
    - LLM with structured output + fixed rubric
    
    Never free-form "give it a score" prompts.
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: ChromaVectorStore
    ):
        self.llm = llm_provider
        self.embeddings = embedding_provider
        self.vector_store = vector_store
        
        # Default weights (configurable)
        self.default_weights = {
            "topic_relevance": 0.20,
            "keyword_relevance": 0.15,
            "hook_strength": 0.20,
            "audience_relevance": 0.15,
            "caption_quality": 0.15,
            "hashtag_quality": 0.10,
            "content_freshness": 0.05
        }
    
    def score_caption_quality(self, caption: str) -> CaptionAnalysis:
        """
        Deterministic caption quality analysis.
        
        Args:
            caption: Caption text to analyze
        
        Returns:
            CaptionAnalysis with quality metrics
        """
        length = len(caption)
        
        # Check for CTA patterns
        cta_patterns = [
            r'\bclick\b', r'\blink\b', r'\bswipe\b', r'\btap\b',
            r'\bfollow\b', r'\blike\b', r'\bcomment\b', r'\bshare\b',
            r'\btag\b', r'\bdm\b', r'\bsave\b', r'\bcheck out\b'
        ]
        has_cta = any(re.search(pattern, caption.lower()) for pattern in cta_patterns)
        
        # Check for emojis (any character > U+1F300)
        has_emoji = any(ord(char) > 0x1F300 for char in caption)
        
        # Check for line breaks
        has_line_breaks = '\n' in caption
        
        # Simple readability approximation (Flesch reading ease)
        sentences = re.split(r'[.!?]+', caption)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        
        if sentence_count == 0:
            avg_sentence_length = 0
            readability_score = 0.0
        else:
            words = caption.split()
            word_count = len(words)
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
            
            # Simplified Flesch: 206.835 - 1.015(words/sentences) - 84.6(syllables/words)
            # Approximate syllables as word_length / 3
            syllables = sum(max(1, len(word) // 3) for word in words)
            syllables_per_word = syllables / word_count if word_count > 0 else 0
            
            flesch = 206.835 - 1.015 * avg_sentence_length - 84.6 * syllables_per_word
            readability_score = max(0.0, min(100.0, flesch)) / 100.0  # Normalize to 0-1
        
        # Compute quality score (0-1)
        quality_score = 0.0
        
        # Length scoring (optimal 100-500 chars for Instagram)
        if 100 <= length <= 500:
            quality_score += 0.3
        elif length < 100:
            quality_score += 0.15 * (length / 100)
        else:
            quality_score += 0.3 * (1.0 - min(1.0, (length - 500) / 1700))  # Penalty for too long
        
        # CTA bonus
        if has_cta:
            quality_score += 0.25
        
        # Emoji bonus (engagement factor)
        if has_emoji:
            quality_score += 0.15
        
        # Line breaks bonus (readability)
        if has_line_breaks:
            quality_score += 0.15
        
        # Readability bonus
        quality_score += 0.15 * readability_score
        
        return CaptionAnalysis(
            length=length,
            has_cta=has_cta,
            has_emoji=has_emoji,
            has_line_breaks=has_line_breaks,
            readability_score=readability_score,
            sentence_count=sentence_count,
            avg_sentence_length=avg_sentence_length,
            quality_score=min(1.0, quality_score)  # Cap at 1.0
        )
    
    def score_hook_strength(self, hook: str, target_audience: str | None = None) -> float:
        """
        LLM-based hook strength scoring with structured output.
        
        Args:
            hook: Hook text (first line/sentence of caption or video opening)
            target_audience: Optional audience description for relevance scoring
        
        Returns:
            Normalized hook strength score (0-1)
        """
        prompt = f"""Evaluate this social media hook using the rubric below.

Hook: "{hook}"
"""
        
        if target_audience:
            prompt += f"\nTarget audience: {target_audience}"
        
        prompt += """

Rate the hook on these criteria (1-10 for each):

1. Attention Score: Does it grab attention in the first 2 seconds?
2. Curiosity Score: Does it create a curiosity gap that makes you want to keep reading/watching?
3. Relevance Score: Is it relevant and valuable to the target audience?
4. Clarity Score: Is the value proposition clear?
5. Overall Score: Overall hook strength

Provide brief reasoning for your scores."""
        
        system = "You are an expert social media content strategist evaluating hooks objectively."
        
        try:
            # Use structured output with Pydantic schema
            result = self.llm.structured_output(prompt, HookRubric, system=system)
            
            # Normalize overall score to 0-1
            return result.overall_score / 10.0
        except Exception as e:
            # Fallback: basic length/engagement heuristic
            has_question = '?' in hook
            has_number = any(char.isdigit() for char in hook)
            hook_length = len(hook)
            
            score = 0.3  # Base score
            if has_question:
                score += 0.2
            if has_number:
                score += 0.2
            if 30 <= hook_length <= 100:
                score += 0.3
            
            return min(1.0, score)
    
    def score_topic_relevance(
        self,
        content_text: str,
        brand_pillars: List[str] | None = None
    ) -> float:
        """
        Score topic relevance using embedding similarity.
        
        Args:
            content_text: Content to score
            brand_pillars: List of brand content pillar descriptions
        
        Returns:
            Topic relevance score (0-1)
        """
        if not brand_pillars or len(brand_pillars) == 0:
            return 0.5  # Neutral score if no pillars defined
        
        try:
            # Get embeddings
            content_embedding = self.embeddings.embed_text(content_text)
            pillar_embeddings = self.embeddings.embed_texts(brand_pillars)
            
            # Compute cosine similarity with each pillar
            from numpy import dot
            from numpy.linalg import norm
            
            similarities = []
            for pillar_emb in pillar_embeddings:
                similarity = dot(content_embedding, pillar_emb) / (
                    norm(content_embedding) * norm(pillar_emb)
                )
                similarities.append(similarity)
            
            # Return max similarity (best pillar match)
            return max(similarities)
        
        except Exception as e:
            return 0.5  # Neutral fallback
    
    def score_content_freshness(
        self,
        content_text: str,
        top_k: int = 10,
        similarity_threshold: float = 0.85
    ) -> float:
        """
        Score content freshness by checking for near-duplicates.
        Penalizes content that's too similar to recent posts.
        
        Args:
            content_text: Content to check
            top_k: Number of recent posts to compare against
            similarity_threshold: Threshold for considering content a duplicate
        
        Returns:
            Freshness score (0-1), where 1 = completely fresh, 0 = duplicate
        """
        try:
            # Get embedding
            content_embedding = self.embeddings.embed_text(content_text)
            
            # Search vector store for similar content
            results = self.vector_store.search(
                query_embedding=content_embedding,
                n_results=top_k
            )
            
            if not results.get("distances") or len(results["distances"]) == 0:
                return 1.0  # No similar content found = perfectly fresh
            
            # Convert distances to similarities (1 - distance)
            max_similarity = 1.0 - min(results["distances"])
            
            if max_similarity >= similarity_threshold:
                # Too similar to existing content
                return 1.0 - max_similarity  # Lower score for high similarity
            else:
                # Fresh enough
                return 1.0 - (max_similarity * 0.3)  # Small penalty for moderate similarity
        
        except Exception as e:
            return 1.0  # Benefit of doubt if check fails
    
    def compute_seo_score(
        self,
        caption: str,
        hook: str | None = None,
        keywords: List[str] | None = None,
        hashtags: List[str] | None = None,
        brand_pillars: List[str] | None = None,
        target_audience: str | None = None,
        weights: Dict[str, float] | None = None
    ) -> SEOScore:
        """
        Compute complete SEO score for content.
        
        Args:
            caption: Full caption text
            hook: Hook text (first line/opening). If None, extracts from caption
            keywords: List of target keywords
            hashtags: List of hashtags used
            brand_pillars: Brand content pillar descriptions
            target_audience: Target audience description
            weights: Optional custom weights (uses defaults if None)
        
        Returns:
            Complete SEO score breakdown
        """
        # Use default weights if not provided
        weights = weights or self.default_weights
        
        # Extract hook if not provided (first line or first sentence)
        if not hook:
            lines = caption.split('\n')
            hook = lines[0] if lines else caption[:100]
        
        # Initialize details dict
        details = {}
        
        # 1. Caption quality (deterministic)
        caption_analysis = self.score_caption_quality(caption)
        caption_quality = caption_analysis.quality_score
        details["caption_analysis"] = caption_analysis.dict()
        
        # 2. Hook strength (LLM-based)
        hook_strength = self.score_hook_strength(hook, target_audience)
        details["hook_strength_raw"] = hook_strength
        
        # 3. Topic relevance (embedding similarity)
        topic_relevance = self.score_topic_relevance(caption, brand_pillars)
        details["topic_relevance_raw"] = topic_relevance
        
        # 4. Content freshness (duplicate detection)
        content_freshness = self.score_content_freshness(caption)
        details["content_freshness_raw"] = content_freshness
        
        # 5. Keyword relevance (placeholder - will implement in keyword service)
        keyword_relevance = 0.5  # Neutral for now
        details["keyword_relevance_note"] = "Keyword matching not yet implemented"
        
        # 6. Audience relevance (embedding similarity)
        if target_audience:
            audience_relevance = self.score_topic_relevance(caption, [target_audience])
        else:
            audience_relevance = 0.5  # Neutral if no audience defined
        details["audience_relevance_raw"] = audience_relevance
        
        # 7. Hashtag quality (placeholder - will implement in hashtag service)
        hashtag_quality = 0.5  # Neutral for now
        details["hashtag_quality_note"] = "Hashtag performance tracking not yet implemented"
        
        # Compute weighted overall score
        overall_score = (
            weights["topic_relevance"] * topic_relevance +
            weights["keyword_relevance"] * keyword_relevance +
            weights["hook_strength"] * hook_strength +
            weights["audience_relevance"] * audience_relevance +
            weights["caption_quality"] * caption_quality +
            weights["hashtag_quality"] * hashtag_quality +
            weights["content_freshness"] * content_freshness
        ) * 100  # Scale to 0-100
        
        return SEOScore(
            overall_score=round(overall_score, 2),
            topic_relevance=round(topic_relevance, 3),
            keyword_relevance=round(keyword_relevance, 3),
            hook_strength=round(hook_strength, 3),
            audience_relevance=round(audience_relevance, 3),
            caption_quality=round(caption_quality, 3),
            hashtag_quality=round(hashtag_quality, 3),
            content_freshness=round(content_freshness, 3),
            weights=weights,
            details=details
        )
