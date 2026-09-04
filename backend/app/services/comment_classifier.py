# backend/app/services/comment_classifier.py — Comment classification service
# Cost classification: FREE + OPEN SOURCE

"""
Comment classification service for Instagram comments.

Implements a two-tier classification pipeline:
1. Rule-based fast path for obvious cases (emoji-only, very short, spam patterns)
2. LLM-based semantic classification for nuanced cases

Classification schema (13 classes):
- POSITIVE, NEGATIVE, QUESTION, PRODUCT_QUESTION, SUPPORT
- COMPLAINT, SPAM, TROLL, OFF_TOPIC, PRAISE, REQUEST
- SENSITIVE, UNKNOWN
"""

import re
from typing import Protocol, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.providers import LLMProvider


class CommentClassification(str):
    """Enum for comment classification classes."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    QUESTION = "question"
    PRODUCT_QUESTION = "product_question"
    SUPPORT = "support"
    COMPLAINT = "complaint"
    SPAM = "spam"
    TROLL = "troll"
    OFF_TOPIC = "off_topic"
    PRAISE = "praise"
    REQUEST = "request"
    SENSITIVE = "sensitive"
    UNKNOWN = "unknown"


class ClassificationResult(BaseModel):
    """Result of comment classification."""
    classification: str = Field(
        description="The predicted classification category"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the classification"
    )
    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen"
    )
    is_sensitive: bool = Field(
        description="Whether the comment contains sensitive content requiring human review"
    )


class CommentClassifier(Protocol):
    """Protocol for comment classification providers."""
    
    async def classify(
        self,
        comment_text: str,
        comment_id: Optional[str] = None
    ) -> ClassificationResult:
        """Classify a comment and return result with confidence score."""
        ...


class RuleBasedClassifier:
    """Rule-based classifier for fast-path classification."""
    
    # Spam patterns
    SPAM_PATTERNS = [
        r'^https?://[^\s]+',
        r'buy\s+now|click\s+here|limited\s+offer',
        r'congratulations\s+you\s+won',
        r'free\s+(gift|money| prize)',
        r'\b(click|clicking)\b',
    ]
    
    # Troll/abuse patterns
    TROLL_PATTERNS = [
        r'\b(hate|stupid|idiot|dumb)\b',
        r'\b(f*ck|s*ck|b*tch|p*ssy|c*nt|wh*re)\b',
        r'\b(kill|die|dead)\b',
        r'\b(loser|waste|failure)\b',
    ]
    
    # Negativity patterns
    NEGATIVE_PATTERNS = [
        r'\b(hate|dislike|bad|terrible|awful|horrible|worst|useless)\b',
        r'\b(complain|angry|frustrated|disappointed)\b',
        r'\b(not\s+good|not\s+work|broken|defect)\b',
    ]
    
    # Positive patterns
    POSITIVE_PATTERNS = [
        r'\b(great|amazing|love|like|best|awesome|fantastic|wonderful|beautiful)\b',
        r'\b(appreciate|thank|thanks)\b',
        r'\b(happy|excited|glad)\b',
    ]
    
    # Question patterns
    QUESTION_PATTERNS = [
        r'\b(how|what|when|where|why|which|who)\b\?',
        r'\b(can|could|would|should|do|does)\b\s+\w+\?',
    ]
    
    # Product question patterns
    PRODUCT_PATTERNS = [
        r'\b(price|cost|buy|purchase|order)\b',
        r'\b(stock|available|delivery|shipping)\b',
        r'\b(model|version|type|variant)\b',
        r'\b(size|color|material|weight)\b',
    ]
    
    # Support patterns
    SUPPORT_PATTERNS = [
        r'\b(help|support|problem|issue|error|bug|fix)\b',
        r'\b(login|access|account|password)\b',
    ]
    
    # Request patterns
    REQUEST_PATTERNS = [
        r'\b(please|want|need|looking\s+for|seeking)\b',
        r'\b(suggest|recommend|advice)\b',
    ]
    
    # Sensitive content indicators
    SENSITIVE_PATTERNS = [
        r'\b(medical|doctor|health|prescription|drug)\b',
        r'\b(money|bank|account|credit|card)\b',
        r'\b(password|secret|private|confidential)\b',
        r'\b(scam|fraud|illegal|crime)\b',
        r'\b(legal|court|lawyer|attorney)\b',
    ]
    
    def __init__(self):
        """Initialize rule patterns compiled."""
        self._spam_compiled = [re.compile(p, re.IGNORECASE) for p in self.SPAM_PATTERNS]
        self._troll_compiled = [re.compile(p, re.IGNORECASE) for p in self.TROLL_PATTERNS]
        self._negative_compiled = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_PATTERNS]
        self._positive_compiled = [re.compile(p, re.IGNORECASE) for p in self.POSITIVE_PATTERNS]
        self._question_compiled = [re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS]
        self._product_compiled = [re.compile(p, re.IGNORECASE) for p in self.PRODUCT_PATTERNS]
        self._support_compiled = [re.compile(p, re.IGNORECASE) for p in self.SUPPORT_PATTERNS]
        self._request_compiled = [re.compile(p, re.IGNORECASE) for p in self.REQUEST_PATTERNS]
        self._sensitive_compiled = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]
    
    def classify(self, text: str) -> Optional[ClassificationResult]:
        """
        Attempt rule-based classification.
        Returns None if rules can't determine confidently.
        """
        text_lower = text.lower().strip()
        text_clean = re.sub(r'[^\w\s]', '', text_lower)
        
        if not text_clean:
            return None
        
        # Fast path: very short text (likely spam or emoji)
        if len(text_clean.split()) <= 2:
            if re.match(r'^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+$', text):
                return ClassificationResult(
                    classification=CommentClassification.POSITIVE,
                    confidence=0.7,
                    reasoning="Emoji reaction, interpreted as positive",
                    is_sensitive=False
                )
            if re.match(r'^https?://[^\s]+$', text):
                return ClassificationResult(
                    classification=CommentClassification.SPAM,
                    confidence=0.95,
                    reasoning="URL-only comment, high spam probability",
                    is_sensitive=False
                )
            return None
        
        # Check for sensitive content first
        for pattern in self._sensitive_compiled:
            if pattern.search(text):
                return ClassificationResult(
                    classification=CommentClassification.SENSITIVE,
                    confidence=0.85,
                    reasoning="Contains sensitive keywords requiring human review",
                    is_sensitive=True
                )
        
        # Check spam patterns
        spam_matches = sum(1 for p in self._spam_compiled if p.search(text_lower))
        if spam_matches >= 2:
            return ClassificationResult(
                classification=CommentClassification.SPAM,
                confidence=0.8,
                reasoning=f"Matched {spam_matches} spam patterns",
                is_sensitive=False
            )
        
        # Check troll patterns
        troll_matches = sum(1 for p in self._troll_compiled if p.search(text_lower))
        if troll_matches >= 1:
            return ClassificationResult(
                classification=CommentClassification.TROLL,
                confidence=0.75,
                reasoning=f"Matched {troll_matches} troll patterns",
                is_sensitive=True
            )
        
        # Check question patterns
        question_matches = sum(1 for p in self._question_compiled if p.search(text_lower))
        if question_matches >= 1:
            if any(p.search(text_lower) for p in self._product_compiled):
                return ClassificationResult(
                    classification=CommentClassification.PRODUCT_QUESTION,
                    confidence=0.7,
                    reasoning="Question about product details",
                    is_sensitive=False
                )
            return ClassificationResult(
                classification=CommentClassification.QUESTION,
                confidence=0.7,
                reasoning="General question",
                is_sensitive=False
            )
        
        # Check positive patterns
        positive_matches = sum(1 for p in self._positive_compiled if p.search(text_lower))
        if positive_matches >= 2:
            return ClassificationResult(
                classification=CommentClassification.PRAISE,
                confidence=0.75,
                reasoning=f"Matched {positive_matches} positive patterns",
                is_sensitive=False
            )
        
        # Check negative patterns
        negative_matches = sum(1 for p in self._negative_compiled if p.search(text_lower))
        if negative_matches >= 2:
            return ClassificationResult(
                classification=CommentClassification.NEGATIVE,
                confidence=0.7,
                reasoning=f"Matched {negative_matches} negative patterns",
                is_sensitive=False
            )
        
        # Check support patterns
        if any(p.search(text_lower) for p in self._support_compiled):
            return ClassificationResult(
                classification=CommentClassification.SUPPORT,
                confidence=0.7,
                reasoning="Customer support request",
                is_sensitive=False
            )
        
        # Check request patterns
        if any(p.search(text_lower) for p in self._request_compiled):
            return ClassificationResult(
                classification=CommentClassification.REQUEST,
                confidence=0.65,
                reasoning="Request or suggestion",
                is_sensitive=False
            )
        
        # Default to UNKNOWN
        return None


class LLMLessCommentClassifier:
    """
    Comment classifier using rule-based approach + optional LLM fallback.
    
    This avoids LLM calls for straightforward cases, keeping costs low.
    Only escalates to LLM when rules are inconclusive or confidence is low.
    """
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        use_llm_fallback: bool = True
    ):
        """Initialize classifier with optional LLM provider."""
        self.rule_classifier = RuleBasedClassifier()
        self.llm_provider = llm_provider
        self.use_llm_fallback = use_llm_fallback
    
    async def classify(
        self,
        comment_text: str,
        comment_id: Optional[str] = None
    ) -> ClassificationResult:
        """
        Classify a comment using rules first, fallback to LLM if needed.
        """
        rule_result = self.rule_classifier.classify(comment_text)
        
        if rule_result is not None:
            if rule_result.confidence >= 0.65:
                return rule_result
            
            if self.use_llm_fallback and self.llm_provider:
                return await self._classify_with_llm(comment_text)
        
        if self.use_llm_fallback and self.llm_provider:
            return await self._classify_with_llm(comment_text)
        
        return ClassificationResult(
            classification=CommentClassification.UNKNOWN,
            confidence=0.0,
            reasoning="No classification rule matched and LLM not available",
            is_sensitive=False
        )
    
    async def _classify_with_llm(self, comment_text: str) -> ClassificationResult:
        """Classify using LLM provider."""
        prompt = f"""Classify this Instagram comment into one of these categories:
- POSITIVE, NEGATIVE, QUESTION, PRODUCT_QUESTION, SUPPORT
- COMPLAINT, SPAM, TROLL, OFF_TOPIC, PRAISE, REQUEST
- SENSITIVE, UNKNOWN

Return a JSON object with:
- classification: one of the categories above
- confidence: 0.0-1.0
- reasoning: 1-2 sentence explanation
- is_sensitive: true if contains sensitive content requiring human review

Comment: {comment_text}

Format strictly as JSON, no other text."""

        result = await self.llm_provider.structured_output(
            prompt=prompt,
            schema=ClassificationResult
        )
        
        return result
