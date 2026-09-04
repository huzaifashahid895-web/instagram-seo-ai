# backend/app/api/ai_studio.py
# Cost classification: FREE + OPEN SOURCE
"""
AI Studio API endpoints - content generation with LLM + RAG
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.llm.ollama_provider import OllamaProvider
from app.services.embeddings.sentence_transformers_provider import SentenceTransformersProvider
from app.services.vector_store.chroma_store import ChromaVectorStore
from app.services.rag import RAGService
from app.services.tts.piper_provider import PiperTTSProvider
from app.services.stt.faster_whisper_provider import FasterWhisperProvider
from app.services.image_gen.comfyui_provider import ComfyUIImageProvider
from app.services.generation.pipeline import (
    ContentGenerationPipeline,
    ContentRequest,
    ContentGenerationResult,
)


router = APIRouter()


# Request/Response models
class IdeationRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500, description="Content topic or theme")
    brand_profile_id: str | None = Field(None, description="Optional brand profile filter")
    num_ideas: int = Field(5, ge=1, le=20, description="Number of ideas to generate")
    temperature: float = Field(0.8, ge=0.0, le=2.0, description="LLM temperature")


class IdeationResponse(BaseModel):
    ideas: List[str]
    topic: str


class CaptionRequest(BaseModel):
    content_description: str = Field(..., min_length=10, max_length=2000, description="Description of content")
    style: str = Field("engaging", description="Caption style (engaging, professional, casual, etc.)")
    max_length: int = Field(2200, ge=100, le=2200, description="Maximum caption length")
    include_hashtags: bool = Field(True, description="Include hashtags")
    brand_voice: str | None = Field(None, max_length=500, description="Brand voice description")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="LLM temperature")


class CaptionResponse(BaseModel):
    caption: str
    character_count: int


class HealthCheckResponse(BaseModel):
    ollama_available: bool
    models_available: List[str]
    embedding_model_loaded: bool
    vector_store_available: bool


# Dependency injection for RAG service
def get_rag_service() -> RAGService:
    """Initialize and return RAG service with dependencies"""
    llm = OllamaProvider()
    embeddings = SentenceTransformersProvider()
    vector_store = ChromaVectorStore()
    return RAGService(llm, embeddings, vector_store)


@router.post("/ideation", response_model=IdeationResponse)
def generate_ideas(
    request: IdeationRequest,
    current_user: User = Depends(get_current_user),
    rag: RAGService = Depends(get_rag_service)
) -> IdeationResponse:
    """
    Generate content ideas based on topic and existing content library.
    Uses RAG to find similar content and LLM to generate fresh ideas.
    """
    try:
        ideas = rag.generate_ideas_from_content(
            topic=request.topic,
            brand_profile_id=request.brand_profile_id,
            num_ideas=request.num_ideas,
            temperature=request.temperature
        )
        
        return IdeationResponse(ideas=ideas, topic=request.topic)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate ideas: {str(e)}"
        )


@router.post("/caption", response_model=CaptionResponse)
def generate_caption(
    request: CaptionRequest,
    current_user: User = Depends(get_current_user),
    rag: RAGService = Depends(get_rag_service)
) -> CaptionResponse:
    """
    Generate social media caption for content.
    Uses RAG to reference similar content style and LLM to write caption.
    """
    try:
        caption = rag.generate_caption(
            content_description=request.content_description,
            style=request.style,
            max_length=request.max_length,
            include_hashtags=request.include_hashtags,
            brand_voice=request.brand_voice,
            temperature=request.temperature
        )
        
        return CaptionResponse(
            caption=caption.strip(),
            character_count=len(caption.strip())
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate caption: {str(e)}"
        )


@router.get("/health", response_model=HealthCheckResponse)
def health_check(
    current_user: User = Depends(get_current_user),
    rag: RAGService = Depends(get_rag_service)
) -> HealthCheckResponse:
    """
    Check health of AI services (Ollama, embeddings, vector store).
    """
    # Check Ollama
    ollama_available = rag.llm.health_check()
    models_available = rag.llm.list_models() if ollama_available else []
    
    # Check embeddings
    try:
        _ = rag.embeddings.get_embedding_dimension()
        embedding_model_loaded = True
    except Exception:
        embedding_model_loaded = False
    
    # Check vector store
    try:
        rag.vector_store.list_collections()
        vector_store_available = True
    except Exception:
        vector_store_available = False
    
    return HealthCheckResponse(
        ollama_available=ollama_available,
        models_available=models_available,
        embedding_model_loaded=embedding_model_loaded,
        vector_store_available=vector_store_available
    )


# Dependency injection for content generation pipeline
def get_content_pipeline() -> ContentGenerationPipeline:
    """Initialize and return content generation pipeline with all dependencies"""
    llm = OllamaProvider()
    embeddings = SentenceTransformersProvider()
    vector_store = ChromaVectorStore()
    tts = PiperTTSProvider()
    stt = FasterWhisperProvider()
    
    # Image generation is optional (hardware-gated)
    try:
        image_gen = ComfyUIImageProvider()
        if not image_gen.check_available():
            image_gen = None
    except Exception:
        image_gen = None
    
    return ContentGenerationPipeline(
        llm_provider=llm,
        embedding_provider=embeddings,
        vector_store=vector_store,
        tts_provider=tts,
        stt_provider=stt,
        image_provider=image_gen,
    )


@router.post("/generate", response_model=ContentGenerationResult)
async def generate_content(
    request: ContentRequest,
    current_user: User = Depends(get_current_user),
    pipeline: ContentGenerationPipeline = Depends(get_content_pipeline)
) -> ContentGenerationResult:
    """
    Generate complete social media content from topic.
    
    Full pipeline: Topic → Script → Audio → Subtitles → Images (optional) → Final Video
    
    This is a long-running operation (30 seconds to several minutes depending on:
    - Script complexity
    - Audio duration
    - Image generation (if enabled, hardware-gated)
    - Video assembly operations
    
    Hardware notes:
    - Script + Audio + Subtitles: Works on any system (fast on CPU)
    - Image generation: Requires ComfyUI server running (slow on CPU, 1-5+ min/image)
    - Video assembly: FFmpeg operations are fast
    """
    try:
        result = await pipeline.generate(request)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {str(e)}"
        )


@router.get("/generate/info")
def get_generation_info(
    current_user: User = Depends(get_current_user),
    pipeline: ContentGenerationPipeline = Depends(get_content_pipeline)
) -> dict:
    """
    Get information about content generation pipeline capabilities.
    
    Returns available features, supported formats, and provider status.
    """
    return pipeline.get_info()


# Additional endpoints for frontend compatibility
class ScriptRequest(BaseModel):
    prompt: str = Field(..., description="Script prompt or topic")
    target_duration_seconds: int = Field(60, ge=10, le=300, description="Target duration in seconds")


class ScriptResponse(BaseModel):
    id: str
    prompt: str
    script_text: str
    estimated_duration_seconds: int
    word_count: int


@router.post("/generate-script", response_model=ScriptResponse)
async def generate_script(
    request: ScriptRequest,
    current_user: User = Depends(get_current_user)
) -> ScriptResponse:
    """
    Generate a video script from a prompt.
    Uses Ollama + Qwen2.5 for text generation.
    """
    try:
        import uuid
        from app.config import settings
        from app.services.llm.ollama_provider import OllamaProvider
        
        llm = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL
        )
        
        system_prompt = f"""You are a professional social media script writer.
Generate an engaging video script based on the user's prompt.
The script should be approximately {request.target_duration_seconds} seconds when spoken (about {request.target_duration_seconds * 2.5} words).
Make it conversational, engaging, and suitable for Instagram/TikTok."""
        
        script = llm.generate(
            prompt=f"Create a video script about: {request.prompt}",
            system=system_prompt,
            temperature=0.8
        )
        
        word_count = len(script.split())
        estimated_duration = int(word_count / 2.5)  # ~2.5 words per second
        
        return ScriptResponse(
            id=str(uuid.uuid4()),
            prompt=request.prompt,
            script_text=script.strip(),
            estimated_duration_seconds=estimated_duration,
            word_count=word_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate script: {str(e)}"
        )


class CaptionGenerationRequest(BaseModel):
    content_id: str = Field(..., description="Content asset ID to generate caption for")
    platform: str = Field("instagram", description="Target platform")


class CaptionGenerationResponse(BaseModel):
    caption: str
    hashtags: List[str]
    character_count: int


@router.post("/generate-caption", response_model=CaptionGenerationResponse)
async def generate_caption_for_content(
    request: CaptionGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CaptionGenerationResponse:
    """
    Generate a caption for specific content.
    Uses Ollama + Qwen2.5 for caption generation.
    """
    try:
        from app.config import settings
        from app.services.llm.ollama_provider import OllamaProvider
        from app.models.content_asset import ContentAsset
        import uuid
        
        # Get content asset
        asset = db.query(ContentAsset).filter(
            ContentAsset.id == uuid.UUID(request.content_id)
        ).first()
        
        if not asset:
            raise HTTPException(status_code=404, detail="Content not found")
        
        llm = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL
        )
        
        system_prompt = f"""You are a professional social media caption writer for {request.platform}.
Generate an engaging caption that:
- Is attention-grabbing and encourages engagement
- Uses appropriate emojis
- Includes relevant hashtags (5-10)
- Stays within 2200 characters
- Matches the platform's style"""
        
        content_info = f"Content type: {asset.media_type}, Filename: {asset.filename}"
        if asset.transcript:
            content_info += f"\nTranscript: {asset.transcript[:500]}"
        
        prompt = f"Generate an Instagram caption for this content:\n{content_info}"
        
        caption_text = llm.generate(
            prompt=prompt,
            system=system_prompt,
            temperature=0.7
        )
        
        # Extract hashtags from caption
        import re
        hashtags = re.findall(r'#\w+', caption_text)
        
        return CaptionGenerationResponse(
            caption=caption_text.strip(),
            hashtags=hashtags,
            character_count=len(caption_text.strip())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate caption: {str(e)}"
        )


class VideoProductionRequest(BaseModel):
    script_id: str = Field(..., description="Script ID to produce video from")
    voice_id: str | None = Field(None, description="Optional voice ID for TTS")


class VideoProductionResponse(BaseModel):
    job_id: str
    status: str
    message: str


@router.post("/produce-video", response_model=VideoProductionResponse)
async def produce_video(
    request: VideoProductionRequest,
    current_user: User = Depends(get_current_user)
) -> VideoProductionResponse:
    """
    Produce a video from a script (TTS + video assembly).
    This is a placeholder - full implementation requires video generation pipeline.
    """
    import uuid
    
    # For now, return a stub response
    job_id = str(uuid.uuid4())
    
    return VideoProductionResponse(
        job_id=job_id,
        status="pending",
        message="Video production is not yet implemented. Requires TTS + video generation pipeline setup."
    )
