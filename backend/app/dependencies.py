# backend/app/dependencies.py — Dependency injection for AI providers
# Cost classification: FREE + OPEN SOURCE

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings, settings
from app.services.llm.ollama_provider import OllamaProvider
from app.services.embeddings.sentence_transformers_provider import SentenceTransformersProvider
from app.services.stt.faster_whisper_provider import FasterWhisperProvider
from app.services.tts.piper_provider import PiperTTSProvider
from app.services.vision.clip_vision_provider import CLIPVisionProvider
from app.services.vector_store.chroma_store import ChromaVectorStore
from app.services.image_gen.comfyui_provider import ComfyUIImageProvider
from app.services.video_gen.stub_provider import StubVideoGenProvider
from app.services.providers import (
    LLMProvider,
    EmbeddingProvider,
    STTProvider,
    TTSProvider,
    VisionProvider,
    ImageGenProvider,
    VideoGenProvider,
)


# LLM Provider
@lru_cache
def get_llm_provider(cfg: Annotated[Settings, Depends(lambda: settings)]) -> LLMProvider:
    """Get configured LLM provider (Ollama + Qwen2.5)."""
    return OllamaProvider(
        base_url=cfg.OLLAMA_BASE_URL,
        model=cfg.OLLAMA_MODEL,
    )


# Embedding Provider
@lru_cache
def get_embedding_provider(cfg: Annotated[Settings, Depends(lambda: settings)]) -> EmbeddingProvider:
    """Get configured embedding provider (BGE via sentence-transformers)."""
    return SentenceTransformersProvider(
        model_name=cfg.EMBEDDINGS_MODEL,
    )


# Speech-to-Text Provider
@lru_cache
def get_stt_provider(cfg: Annotated[Settings, Depends(lambda: settings)]) -> STTProvider:
    """Get configured STT provider (faster-whisper)."""
    return FasterWhisperProvider(
        model_size=cfg.WHISPER_MODEL,
        device=cfg.WHISPER_DEVICE,
    )


# Text-to-Speech Provider
@lru_cache
def get_tts_provider() -> TTSProvider:
    """Get configured TTS provider (Piper)."""
    return PiperProvider()


# Vision Provider
@lru_cache
def get_vision_provider() -> VisionProvider:
    """Get configured vision provider (OpenCLIP)."""
    return CLIPVisionProvider()


# Vector Store
@lru_cache
def get_vector_store(cfg: Annotated[Settings, Depends(lambda: settings)]) -> ChromaVectorStore:
    """Get configured vector store (Chroma)."""
    return ChromaVectorStore(
        persist_directory=cfg.CHROMA_PERSIST_DIR,
    )


# Image Generation Provider
@lru_cache
def get_image_gen_provider() -> ImageGenProvider:
    """Get configured image generation provider (ComfyUI stub for now)."""
    return ComfyUIProvider()


# Video Generation Provider
@lru_cache
def get_video_gen_provider() -> VideoGenProvider:
    """Get configured video generation provider (stub for now)."""
    return StubVideoGenProvider()


# Convenience type aliases for dependency injection
LLMDep = Annotated[LLMProvider, Depends(get_llm_provider)]
EmbeddingDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
STTDep = Annotated[STTProvider, Depends(get_stt_provider)]
TTSDep = Annotated[TTSProvider, Depends(get_tts_provider)]
VisionDep = Annotated[VisionProvider, Depends(get_vision_provider)]
VectorStoreDep = Annotated[ChromaVectorStore, Depends(get_vector_store)]
ImageGenDep = Annotated[ImageGenProvider, Depends(get_image_gen_provider)]
VideoGenDep = Annotated[VideoGenProvider, Depends(get_video_gen_provider)]
