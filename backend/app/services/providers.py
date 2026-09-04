# backend/app/services/providers.py — Provider abstraction protocols
# Cost classification: FREE + OPEN SOURCE

from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for text generation models."""

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""
        ...

    def stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """Stream text generation token by token."""
        ...

    def structured_output(self, prompt: str, schema: type[BaseModel], **kwargs) -> BaseModel:
        """Generate structured output conforming to a Pydantic schema."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for text/image embedding models."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of text strings."""
        ...

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        ...


@runtime_checkable
class STTProvider(Protocol):
    """Protocol for speech-to-text / transcription models."""

    def transcribe(self, audio_path: str | Path, language: str | None = None) -> "TranscriptResult":
        """Transcribe audio file to text with timestamps."""
        ...


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol for text-to-speech models."""

    def synthesize(self, text: str, voice: str | None = None, **kwargs) -> Path:
        """Synthesize speech from text, return path to generated audio file."""
        ...


@runtime_checkable
class VisionProvider(Protocol):
    """Protocol for vision/image analysis models."""

    def analyze(self, image_path: str | Path) -> "VisionAnalysis":
        """Analyze an image and return structured results."""
        ...

    def caption(self, image_path: str | Path) -> str:
        """Generate a natural language caption for an image."""
        ...

    def extract_tags(self, image_path: str | Path) -> list[str]:
        """Extract semantic tags/labels from an image."""
        ...


@runtime_checkable
class ImageGenProvider(Protocol):
    """Protocol for image generation models."""

    def generate(self, prompt: str, **kwargs) -> Path:
        """Generate an image from a text prompt, return path to generated file."""
        ...


@runtime_checkable
class VideoGenProvider(Protocol):
    """Protocol for video generation models."""

    def generate(self, prompt: str, **kwargs) -> Path:
        """Generate a video from a text prompt, return path to generated file."""
        ...


@runtime_checkable
class SocialPlatform(Protocol):
    """Protocol for social media platform integrations."""

    def publish_post(self, **kwargs) -> "PublishResult":
        """Publish a post (image/carousel) to the platform."""
        ...

    def publish_video(self, **kwargs) -> "PublishResult":
        """Publish a video (reel/story) to the platform."""
        ...

    def get_comments(self, post_id: str, **kwargs) -> list["Comment"]:
        """Fetch comments for a post."""
        ...

    def reply_to_comment(self, comment_id: str, text: str, **kwargs) -> "Comment":
        """Reply to a comment."""
        ...

    def get_analytics(self, post_id: str, **kwargs) -> "PostAnalytics":
        """Get analytics/insights for a post."""
        ...


# Structured result types for provider outputs


class TranscriptSegment(BaseModel):
    """A single segment of transcribed speech."""

    start: float  # seconds
    end: float  # seconds
    text: str


class TranscriptResult(BaseModel):
    """Complete transcription result."""

    text: str  # full transcript
    segments: list[TranscriptSegment]
    language: str | None = None
    duration: float | None = None


class VisionAnalysis(BaseModel):
    """Structured vision analysis result."""

    caption: str | None = None
    tags: list[str] = []
    objects: list[str] = []
    scene_type: str | None = None
    dominant_colors: list[str] = []
    text_detected: str | None = None
    embedding: list[float] | None = None


class PublishResult(BaseModel):
    """Result from publishing content to a social platform."""

    platform_post_id: str  # Platform-specific post ID
    permalink: str | None = None  # Public URL to the post
    published_at: str | None = None  # ISO timestamp
    status: str = "published"  # published, pending, failed


class Comment(BaseModel):
    """A comment on a social media post."""

    id: str  # Platform comment ID
    post_id: str  # Platform post ID
    text: str
    username: str
    user_id: str | None = None
    timestamp: str | None = None  # ISO timestamp
    like_count: int = 0
    is_hidden: bool = False
    replies: list["Comment"] = []


class PostAnalytics(BaseModel):
    """Analytics/insights for a social media post."""

    post_id: str
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0
    fetched_at: str | None = None  # ISO timestamp
