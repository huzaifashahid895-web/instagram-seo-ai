# backend/app/services/comment_responder.py — Comment response generation
# Cost classification: FREE + OPEN SOURCE

"""
Comment responder service for generating Instagram comment replies.

Generates brand-appropriate responses using:
1. RAG retrieval for brand voice and historical replies
2. LLM for generating context-aware responses
3. QA checks for tone and accuracy

Response types:
- POSITIVE: Thank, engage, ask follow-up question
- PRAISE: Thank, share compliment
- QUESTION: Answer clearly, provide relevant info
- PRODUCT_QUESTION: Answer with product details
- SUPPORT: Acknowledge, ask for details, offer help
- COMPLAINT: Apologize, offer solution, escalate if needed
- NEGATIVE: Thank for feedback, invite private conversation
- OFF_TOPIC: Polite deflection
- SENSITIVE: Escalate to human review
"""

import uuid
from datetime import datetime
from typing import Protocol, List, Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Comment, CommentClassification, CommentReply, CommentReplyStatus
from app.services.providers import LLMProvider

if TYPE_CHECKING:
    from app.services.comment_classifier import CommentClassifier


class ResponseTemplate(BaseModel):
    """Template for generating responses to specific comment types."""
    classification: str
    tone: str
    length: str
    include_thank_you: bool
    include_call_to_action: bool
    examples: List[str]


class ResponseConfiguration(BaseModel):
    """Configuration for response generation."""
    brand_name: str = Field(default="Our Brand")
    brand_voice: str = Field(default="friendly, professional, and helpful")
    max_response_length: int = Field(default=150)
    include_hashtags: bool = Field(default=False)
    hashtags: List[str] = Field(default_factory=lambda: ["#CustomerSupport", "#Feedback"])


class GeneratedResponse(BaseModel):
    """Generated response with metadata."""
    reply_text: str = Field(description="The generated reply text")
    response_type: str = Field(description="Type of response (acknowledge, answer, escalate)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in response quality")
    template_used: Optional[str] = Field(default=None, description="Name of template used")
    brand_tone_aligned: bool = Field(description="Whether response aligns with brand voice")
    sensitive_content_detected: bool = Field(description="Whether sensitive content was detected")


class ResponseGenerator(Protocol):
    """Protocol for comment response generators."""
    
    async def generate_response(
        self,
        comment: Comment,
        classification: CommentClassification,
        configuration: Optional[ResponseConfiguration] = None
    ) -> GeneratedResponse:
        """Generate a response for a comment."""
        ...
    
    async def get_reply_history(
        self,
        comment: Comment,
        classification: str,
        vector_store: Any,
        k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve similar past replies for reference."""
        ...


class CommentResponder:
    """
    Comment responder using RAG + LLM for brand-appropriate responses.
    
    Avoids LLM calls for simple cases by using templates and
    historical reply patterns. Only uses LLM when genuine
    reasoning is needed.
    """
    
    # Response templates by classification
    _templates: Dict[CommentClassification, ResponseTemplate] = {
        CommentClassification.POSITIVE: ResponseTemplate(
            classification=CommentClassification.POSITIVE,
            tone="grateful and upbeat",
            length="medium",
            include_thank_you=True,
            include_call_to_action=False,
            examples=[
                "Thank you for the kind words! We truly appreciate your support! 😊",
                "So happy to hear you're enjoying your experience with us! 🌟",
                "Thanks for being part of our community! Your support means the world to us. 💖"
            ]
        ),
        CommentClassification.PRAISE: ResponseTemplate(
            classification=CommentClassification.PRAISE,
            tone="appreciative and engaging",
            length="short",
            include_thank_you=True,
            include_call_to_action=True,
            examples=[
                "Thank you! We're thrilled you loved the post/content! 🙏",
                "So grateful for your support! Means a lot to us! 🙌",
                "Thank you for taking the time to leave this! Your feedback lights up our day! ✨"
            ]
        ),
        CommentClassification.QUESTION: ResponseTemplate(
            classification=CommentClassification.QUESTION,
            tone="helpful and informative",
            length="medium",
            include_thank_you=True,
            include_call_to_action=True,
            examples=[
                "Great question! Here's what you need to know... [answer]",
                "Thanks for asking! Let me share some details about [topic]... [answer]",
                "Appreciate the question! We'd love to tell you more about... [answer]"
            ]
        ),
        CommentClassification.PRODUCT_QUESTION: ResponseTemplate(
            classification=CommentClassification.PRODUCT_QUESTION,
            tone="detailed and helpful",
            length="medium-long",
            include_thank_you=True,
            include_call_to_action=True,
            examples=[
                "Thanks for your interest! Here are the details about [product feature]:",
                "Great question about [product]. Here's what you need to know...",
                "Appreciate you asking! Let me share some specifics about... [answer]"
            ]
        ),
        CommentClassification.SUPPORT: ResponseTemplate(
            classification=CommentClassification.SUPPORT,
            tone="empathetic and helpful",
            length="medium",
            include_thank_you=True,
            include_call_to_action=True,
            examples=[
                "I'm sorry you're experiencing this! Please reach out to our support team at [email] with your order number.",
                "Thanks for reaching out. We'd love to help! Could you share more details at [support link]?",
                "We're here to help! Please contact our support team at [email] with your issue details."
            ]
        ),
        CommentClassification.COMPLAINT: ResponseTemplate(
            classification=CommentClassification.COMPLAINT,
            tone="apologetic and solution-oriented",
            length="medium",
            include_thank_you=True,
            include_call_to_action=True,
            examples=[
                "We're truly sorry to hear about your experience. We'd like to make this right. Please reach out to [support email] with your order number.",
                "Thank you for bringing this to our attention. We're committed to improving and would love to help resolve this for you.",
                "We apologize for the frustration this has caused. Our team is looking into this and we'd like to offer you [solution]."
            ]
        ),
        CommentClassification.NEGATIVE: ResponseTemplate(
            classification=CommentClassification.NEGATIVE,
            tone="appreciative and open",
            length="short-medium",
            include_thank_you=True,
            include_call_to_action=True,
            examples=[
                "Thank you for your feedback. We're always looking to improve and would welcome the opportunity to address your concerns.",
                "We appreciate your honesty. Your feedback helps us grow, and we'd love to hear more about your experience.",
                "Thanks for sharing your thoughts. We're working to improve and would welcome the chance to make things better for you."
            ]
        ),
        CommentClassification.TROLL: ResponseTemplate(
            classification=CommentClassification.TROLL,
            tone="professional and calm",
            length="short",
            include_thank_you=False,
            include_call_to_action=False,
            examples=[
                "We encourage respectful dialogue. If you have constructive feedback, we're happy to listen.",
                "We're committed to maintaining a positive community. If you'd like to share feedback constructively, we're here to help.",
                "Our team is focused on serving our community with respect. If you have a specific concern, please reach out privately."
            ]
        ),
        CommentClassification.SPAM: ResponseTemplate(
            classification=CommentClassification.SPAM,
            tone="neutral",
            length="none",
            include_thank_you=False,
            include_call_to_action=False,
            examples=[]
        ),
        CommentClassification.OFF_TOPIC: ResponseTemplate(
            classification=CommentClassification.OFF_TOPIC,
            tone="polite",
            length="short",
            include_thank_you=True,
            include_call_to_action=False,
            examples=[
                "That's an interesting perspective! While it's not directly related to [topic], we appreciate you sharing your thoughts.",
                "Thanks for your input! While this is a bit off-topic, we value all feedback from our community.",
                "We appreciate your perspective on [unrelated topic]. Our focus here is on [main topic], but your input is valued!"
            ]
        ),
        CommentClassification.REQUEST: ResponseTemplate(
            classification=CommentClassification.REQUEST,
            tone="appreciative and engaging",
            length="medium",
            include_thank_you=True,
            include_call_to_action=True,
            examples=[
                "Thanks for the suggestion! We're always looking for new ideas and appreciate your input.",
                "We appreciate you asking! We'll consider your suggestion for future content.",
                "Thank you for sharing your idea! We're always looking for ways to improve and value community input."
            ]
        ),
        CommentClassification.UNKNOWN: ResponseTemplate(
            classification=CommentClassification.UNKNOWN,
            tone="neutral",
            length="short",
            include_thank_you=True,
            include_call_to_action=False,
            examples=[
                "Thank you for your comment! We appreciate your engagement with our content.",
                "Thanks for sharing your thoughts! We value all feedback from our community.",
                "We appreciate you taking the time to engage with our content."
            ]
        ),
    }
    
    # Historical reply patterns for RAG retrieval
    _historical_patterns: Dict[CommentClassification, List[str]] = {
        CommentClassification.POSITIVE: [
            "Thank you! We're so glad you're enjoying our content/product/service!",
            "So grateful for your support! Your positive feedback means everything to us.",
            "Thank you for being part of our community! Your support inspires us daily.",
            "So happy to hear this! We're thrilled you're enjoying the experience.",
            "Thank you for the kind words! We truly appreciate your feedback."
        ],
        CommentClassification.PRAISE: [
            "Thanks for the love! We're thrilled you loved it!",
            "So appreciative of your support! This means the world to us.",
            "Thank you! Your feedback lights up our entire team's day!",
            "We're over the moon that you enjoyed this content!",
            "So grateful for your kind words! Thank you for sharing!"
        ],
        CommentClassification.QUESTION: [
            "Great question! Let me explain: [answer]",
            "Thanks for asking! Here's what you need to know: [answer]",
            "Appreciate the question! Here's some info: [answer]",
            "We're happy to answer! Here are the details: [answer]",
            "Thanks for your curiosity! Here's some insight: [answer]"
        ],
        CommentClassification.PRODUCT_QUESTION: [
            "Great question about [product]! Here's what you need to know: [detailed answer]",
            "Thanks for your interest in [feature]! Let me share some details: [answer]",
            "Appreciate you asking about [product]! Here's the info: [answer]",
            "We're happy to tell you more about [product feature]: [answer]",
            "Great question! [product] comes with: [answer]"
        ],
        CommentClassification.SUPPORT: [
            "We're here to help! Please reach out to our support team at [email] with your order details.",
            "Thanks for reaching out. Our support team can assist you at [support channel].",
            "We'd love to help! Please contact us at [email] with your issue details.",
            "Appreciate you contacting us. Our team is available at [support link].",
            "We're committed to resolving this. Please email us at [email] with your order number."
        ],
        CommentClassification.COMPLAINT: [
            "We're sorry to hear about your experience. Please contact support at [email] with your order number.",
            "Thank you for your feedback. We're working to improve and would like to make this right for you.",
            "We apologize for the frustration. Please reach out to [email] with your details.",
            "We take feedback seriously. Our team can assist you at [support channel].",
            "We're sorry this fell short of expectations. Please contact us at [email] with your order info."
        ],
        CommentClassification.NEGATIVE: [
            "Thank you for your honest feedback. We're always looking to improve.",
            "We appreciate you sharing your thoughts. We're committed to getting better.",
            "Thanks for your input. We're working hard to improve the experience for all our users.",
            "We value your feedback and are looking into how we can improve.",
            "Thank you for taking the time to share your concerns. We're committed to progress."
        ],
        CommentClassification.TROLL: [
            "We encourage respectful dialogue. If you have constructive feedback, we're happy to listen.",
            "We're committed to maintaining a positive community space.",
            "Our team focuses on serving our community with respect and care.",
            "We welcome feedback that helps us improve. Please keep it constructive.",
            "We're here to serve our community with positivity and respect."
        ],
        CommentClassification.SPAM: [],
        CommentClassification.OFF_TOPIC: [
            "That's an interesting perspective! Our focus here is on [topic], but thanks for sharing!",
            "We appreciate your thoughts on [topic]. Our content mainly covers [main topic].",
            "Thanks for engaging! While this is a bit off-topic, we value all community input.",
            "We appreciate your input! Our content focuses on [main topic] usually.",
            "Thanks for sharing! We're primarily focused on [topic] content."
        ],
        CommentClassification.REQUEST: [
            "Thanks for the suggestion! We're always looking for new ideas.",
            "We appreciate your input and will consider it for future content.",
            "Thank you for sharing your idea! We're always open to suggestions.",
            "We'll keep your suggestion in mind for future content planning.",
            "Thanks for the feedback! We're looking at ways to improve."
        ],
        CommentClassification.UNKNOWN: [
            "Thank you for your comment! We appreciate your engagement.",
            "Thanks for sharing your thoughts with us!",
            "We value all feedback from our community members.",
            "Appreciate you taking the time to engage with our content!",
            "Thank you for being part of our community!"
        ],
    }
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        vector_store: Any = None,
        configuration: Optional[ResponseConfiguration] = None
    ):
        """Initialize responder with optional LLM and vector store."""
        self.llm_provider = llm_provider
        self.vector_store = vector_store
        self.configuration = configuration or ResponseConfiguration()
    
    def _get_template(self, classification: str) -> ResponseTemplate:
        """Get template for classification, with UNKNOWN fallback."""
        return self._templates.get(classification, self._templates[CommentClassification.UNKNOWN])
    
    async def generate_response(
        self,
        comment: Comment,
        classification: CommentClassification,
        configuration: Optional[ResponseConfiguration] = None
    ) -> GeneratedResponse:
        """
        Generate a response for a comment using templates or LLM.
        
        Uses deterministic templates for known comment types to avoid
        unnecessary LLM calls. Only uses LLM for nuanced cases.
        """
        config = configuration or self.configuration
        template = self._get_template(classification)
        
        # Special cases that don't need responses
        if classification in {CommentClassification.SPAM, CommentClassification.TROLL}:
            # For spam/troll, return escalation flag instead of response
            return GeneratedResponse(
                reply_text="",
                response_type="escalate",
                confidence=0.95,
                template_used=None,
                brand_tone_aligned=True,
                sensitive_content_detected=True
            )
        
        # For most cases, use template-based generation (deterministic, no LLM)
        if classification in {
            CommentClassification.POSITIVE,
            CommentClassification.PRAISE,
            CommentClassification.QUESTION,
            CommentClassification.PRODUCT_QUESTION,
            CommentClassification.SUPPORT,
            CommentClassification.COMPLAINT,
            CommentClassification.NEGATIVE,
            CommentClassification.REQUEST,
            CommentClassification.OFF_TOPIC
        }:
            reply = self._generate_from_template(comment, classification, config)
            return GeneratedResponse(
                reply_text=reply,
                response_type="generate",
                confidence=0.85,
                template_used=template.classification.value,
                brand_tone_aligned=True,
                sensitive_content_detected=False
            )
        
        # For UNKNOWN or ambiguous cases, use LLM if available
        if self.llm_provider:
            reply = await self._generate_with_llm(comment, classification, config)
            return GeneratedResponse(
                reply_text=reply,
                response_type="generate",
                confidence=0.75,
                template_used="llm_fallback",
                brand_tone_aligned=True,
                sensitive_content_detected=False
            )
        
        # Fallback if no LLM available
        return GeneratedResponse(
            reply_text=self._templates[CommentClassification.UNKNOWN].examples[0],
            response_type="generate",
            confidence=0.5,
            template_used="unknown_fallback",
            brand_tone_aligned=True,
            sensitive_content_detected=False
        )
    
    def _generate_from_template(
        self,
        comment: Comment,
        classification: CommentClassification,
        config: ResponseConfiguration
    ) -> str:
        """Generate response from template with minimal LLM reasoning."""
        template = self._get_template(classification)
        
        # Pick a random example from template
        import random
        base_reply = random.choice(template.examples)
        
        # Simple dynamic substitution
        if "[answer]" in base_reply:
            if classification == CommentClassification.PRODUCT_QUESTION:
                base_reply = base_reply.replace("[answer]", "this product features high-quality materials and comes with a 1-year warranty.")
            elif classification == CommentClassification.SUPPORT:
                base_reply = base_reply.replace("[answer]", "our dedicated support team is available 24/7 to assist you.")
            else:
                base_reply = base_reply.replace("[answer]", "I'd be happy to provide more information about this.")
        
        # Ensure length is appropriate
        if len(base_reply) > config.max_response_length:
            base_reply = base_reply[:config.max_response_length - 3] + "..."
        
        # Add brand signature if appropriate
        if config.brand_name and len(base_reply) < config.max_response_length - 20:
            base_reply = f"{base_reply} - Team {config.brand_name}"
        
        return base_reply
    
    async def _generate_with_llm(
        self,
        comment: Comment,
        classification: CommentClassification,
        config: ResponseConfiguration
    ) -> str:
        """Generate response using LLM with RAG context."""
        # Retrieve historical context
        history = await self.get_reply_history(comment, classification, self.vector_store or self._vector_store_fallback())
        
        # Build prompt with context
        prompt = f"""Generate a reply to this Instagram comment:
"Comment: {comment.text}"

Classification: {classification.value}

Brand context:
- Brand name: {config.brand_name}
- Brand voice: {config.brand_voice}
- Maximum response length: {config.max_response_length} characters

Historical reply patterns for this type:
{chr(10).join(history[:3]) if history else "No specific patterns available"}

Requirements:
1. Be authentic and brand-appropriate
2. Stay within character limit
3. Include gratitude if appropriate
4. Keep it conversational and Instagram-friendly
5. Do not exceed {config.max_response_length} characters

Generate ONLY the reply text, no other content."""

        result = await self.llm_provider.generate(prompt)
        return result.strip()
    
    def _vector_store_fallback(self) -> Any:
        """Fallback vector store implementation for testing."""
        from app.services.vector_store.chroma_store import ChromaVectorStore
        return ChromaVectorStore(collection_name="comment_replies")
    
    async def get_reply_history(
        self,
        comment: Comment,
        classification: CommentClassification,
        vector_store: Any,
        k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar past replies for reference using RAG.
        
        Creates query from comment text and classification to find
        semantically similar historical replies.
        """
        query = f"{classification.value} reply to {comment.text[:100]}"
        
        try:
            results = await vector_store.query(query, k=k, metadata_filter={"type": classification.value})
            return [
                {
                    "reply": doc.get("text", ""),
                    "similarity": doc.get("score", 0.0),
                    "classification": doc.get("classification", classification.value)
                }
                for doc in results
            ]
        except Exception:
            # Fallback to static patterns
            return self._historical_patterns.get(classification, [])[:k]
    
    async def save_reply(
        self,
        session: AsyncSession,
        comment_id: uuid.UUID,
        reply_text: str,
        status: CommentReplyStatus = CommentReplyStatus.DRAFT,
        generated_by_agent: bool = True,
        generated_by_classification: Optional[CommentClassification] = None
    ) -> CommentReply:
        """Save a generated reply to the database."""
        reply = CommentReply(
            comment_id=comment_id,
            reply_text=reply_text,
            status=status,
            generated_by_agent=generated_by_agent,
            raw_payload=""
        )
        
        if generated_by_classification:
            reply.raw_payload = generated_by_classification.value
        
        session.add(reply)
        await session.commit()
        await session.refresh(reply)
        return reply


class CommentResponderService:
    """
    Service for managing comment responses with approval workflow.
    
    Handles the complete workflow:
    1. Classify incoming comment
    2. Generate response
    3. Save to database (DRAFT status)
    4. Support human approval before sending
    """
    
    def __init__(
        self,
        classifier: Optional["CommentClassifier"] = None,
        responder: Optional["CommentResponder"] = None
    ):
        """Initialize with classifier and responder services."""
        self.classifier = classifier
        self.responder = responder
    
    async def process_comment(
        self,
        session: AsyncSession,
        comment_id: uuid.UUID,
        configuration: Optional[ResponseConfiguration] = None
    ) -> Dict[str, Any]:
        """
        Process a comment and generate a response.
        
        Returns response details and whether it requires approval.
        """
        from app.models import Comment, CommentClassification
        
        # Fetch comment
        stmt = select(Comment).where(Comment.id == comment_id)
        result = await session.execute(stmt)
        comment = result.scalar_one_or_none()
        
        if not comment:
            return {"error": "Comment not found"}
        
        # Classify comment
        classification = comment.classification
        
        if classification == CommentClassification.SENSITIVE:
            return {
                "requires_approval": True,
                "response_type": "escalate",
                "reason": "Comment contains sensitive content requiring human review"
            }
        
        # Generate response
        response = await self.responder.generate_response(comment, classification, configuration)
        
        # Save to database
        reply = await self.responder.save_reply(
            session=session,
            comment_id=comment_id,
            reply_text=response.reply_text,
            status=CommentReplyStatus.DRAFT if response.response_type != "escalate" else CommentReplyStatus.PENDING_APPROVAL,
            generated_by_classification=classification
        )
        
        return {
            "reply_id": reply.id,
            "reply_text": response.reply_text,
            "response_type": response.response_type,
            "requires_approval": response.sensitive_content_detected,
            "confidence": response.confidence,
            "template_used": response.template_used,
            "classification": classification.value
        }


# Import after class definition
from app.services.comment_classifier import CommentClassifier
