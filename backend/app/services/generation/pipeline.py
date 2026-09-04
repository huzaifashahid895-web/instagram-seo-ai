# backend/app/services/generation/pipeline.py
# Cost classification: FREE + OPEN SOURCE
"""
Content generation pipeline orchestrator.

Coordinates the full content creation workflow:
1. Script generation (topic → outline → script)
2. Audio synthesis (script → TTS → audio file)
3. Subtitle generation (audio → transcription → SRT/VTT)
4. Image generation (prompts → images, if available)
5. Video assembly (images + audio + subtitles → final video)

This orchestrator handles the deterministic workflow and error recovery,
while delegating creative/AI tasks to specialized providers.
"""

import logging
import uuid
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from app.config import settings
from app.services.providers import (
    LLMProvider,
    EmbeddingProvider,
    TTSProvider,
    STTProvider,
    ImageGenProvider,
)
from app.services.generation.script_generator import (
    ScriptGenerator,
    GeneratedScript,
    ScriptSection,
)
from app.services.generation.subtitle_generator import SubtitleGenerator, SubtitleResult
from app.services.generation.ffmpeg_pipeline import FFmpegPipeline, PipelineResult
from app.services.vector_store.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class ContentRequest(BaseModel):
    """Request for content generation."""
    topic: str
    format_type: str = "reel"  # "reel", "post", "story", "carousel"
    duration_target: str = "15-30 seconds"  # for video content
    voice: str | None = None  # TTS voice name
    generate_images: bool = False  # whether to generate AI images
    image_prompts: List[str] = []  # custom image prompts (if not, derive from script)
    background_music: str | None = None  # path to background music file
    brand_context: str | None = None  # additional brand/product context


class ContentArtifact(BaseModel):
    """A generated content artifact."""
    type: str  # "script", "audio", "subtitle", "image", "video"
    path: str
    metadata: dict = {}


class ContentGenerationResult(BaseModel):
    """Complete content generation result."""
    request_id: str
    topic: str
    format_type: str
    script: GeneratedScript
    artifacts: List[ContentArtifact]
    final_video_path: str | None = None
    success: bool
    error: str | None = None
    generation_time_seconds: float | None = None


class ContentGenerationPipeline:
    """
    Orchestrate full content generation workflow.
    
    High-level flow:
    1. Generate script from topic (LLM + RAG)
    2. Synthesize audio from script (TTS)
    3. Generate subtitles from audio (STT)
    4. Generate images from prompts (optional, hardware-gated)
    5. Assemble final video (FFmpeg: images + audio + subtitles)
    
    Handles errors gracefully and provides partial results when possible.
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: ChromaVectorStore,
        tts_provider: TTSProvider,
        stt_provider: STTProvider,
        image_provider: ImageGenProvider | None = None,
    ):
        """Initialize pipeline with required providers."""
        self.script_generator = ScriptGenerator(
            llm_provider=llm_provider,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        )
        self.tts = tts_provider
        self.stt = stt_provider
        self.image_gen = image_provider
        
        # Initialize sub-services
        self.subtitle_generator = SubtitleGenerator(
            stt_provider=stt_provider,
            output_dir=settings.STORAGE_DIR / "generated" / "subtitles",
        )
        self.ffmpeg = FFmpegPipeline(
            output_dir=settings.STORAGE_DIR / "generated" / "videos",
        )
        
        logger.info("ContentGenerationPipeline initialized")
    
    async def generate(
        self,
        request: ContentRequest,
    ) -> ContentGenerationResult:
        """
        Generate complete content from request.
        
        Args:
            request: Content generation request
            
        Returns:
            ContentGenerationResult with all artifacts and final video
        """
        import time
        start_time = time.time()
        
        request_id = str(uuid.uuid4())
        artifacts: List[ContentArtifact] = []
        
        logger.info(f"Starting content generation: {request_id} | Topic: {request.topic}")
        
        try:
            # Step 1: Generate script
            logger.info(f"[{request_id}] Step 1: Generating script...")
            script = await self._generate_script(request)
            artifacts.append(ContentArtifact(
                type="script",
                path="",  # script is in-memory
                metadata=script.model_dump(),
            ))
            logger.info(f"[{request_id}] Script generated: {script.word_count} words")
            
            # Step 2: Synthesize audio
            logger.info(f"[{request_id}] Step 2: Synthesizing audio...")
            audio_path = await self._synthesize_audio(script, request.voice, request_id)
            artifacts.append(ContentArtifact(
                type="audio",
                path=str(audio_path),
                metadata={"voice": request.voice or "default"},
            ))
            logger.info(f"[{request_id}] Audio generated: {audio_path}")
            
            # Step 3: Generate subtitles
            logger.info(f"[{request_id}] Step 3: Generating subtitles...")
            subtitle_result = await self._generate_subtitles(audio_path, request_id)
            artifacts.append(ContentArtifact(
                type="subtitle",
                path=subtitle_result.file_path,
                metadata={
                    "format": subtitle_result.format,
                    "duration": subtitle_result.duration,
                    "word_count": subtitle_result.word_count,
                },
            ))
            logger.info(f"[{request_id}] Subtitles generated: {subtitle_result.file_path}")
            
            # Step 4: Generate images (optional, hardware-gated)
            image_paths: List[Path] = []
            if request.generate_images and self.image_gen:
                logger.info(f"[{request_id}] Step 4: Generating images...")
                image_paths = await self._generate_images(script, request, request_id)
                for i, img_path in enumerate(image_paths):
                    artifacts.append(ContentArtifact(
                        type="image",
                        path=str(img_path),
                        metadata={"index": i},
                    ))
                logger.info(f"[{request_id}] Generated {len(image_paths)} images")
            else:
                logger.info(f"[{request_id}] Step 4: Skipping image generation (not requested or not available)")
            
            # Step 5: Assemble final video
            logger.info(f"[{request_id}] Step 5: Assembling final video...")
            final_video = await self._assemble_video(
                audio_path=audio_path,
                subtitle_path=Path(subtitle_result.file_path),
                image_paths=image_paths,
                background_music=request.background_music,
                format_type=request.format_type,
                request_id=request_id,
            )
            artifacts.append(ContentArtifact(
                type="video",
                path=str(final_video.output_path),
                metadata={
                    "duration": final_video.duration,
                    "file_size": final_video.file_size,
                    "operations": final_video.operations_applied,
                },
            ))
            logger.info(f"[{request_id}] Final video assembled: {final_video.output_path}")
            
            generation_time = time.time() - start_time
            
            return ContentGenerationResult(
                request_id=request_id,
                topic=request.topic,
                format_type=request.format_type,
                script=script,
                artifacts=artifacts,
                final_video_path=str(final_video.output_path),
                success=True,
                generation_time_seconds=generation_time,
            )
            
        except Exception as e:
            logger.error(f"[{request_id}] Content generation failed: {e}", exc_info=True)
            generation_time = time.time() - start_time
            
            return ContentGenerationResult(
                request_id=request_id,
                topic=request.topic,
                format_type=request.format_type,
                script=script if 'script' in locals() else None,  # type: ignore
                artifacts=artifacts,
                success=False,
                error=str(e),
                generation_time_seconds=generation_time,
            )
    
    async def _generate_script(self, request: ContentRequest) -> GeneratedScript:
        """Generate script from topic."""
        additional_context = ""
        if request.brand_context:
            additional_context = f"\n\nBrand Context:\n{request.brand_context}"
        
        script = self.script_generator.generate_script(
            topic=request.topic,
            format_type=request.format_type,
            target_duration=request.duration_target,
            additional_context=additional_context,
        )
        return script
    
    async def _synthesize_audio(
        self,
        script: GeneratedScript,
        voice: str | None,
        request_id: str,
    ) -> Path:
        """Synthesize audio from script."""
        # Combine all script sections into full text
        full_text = script.full_text
        
        # Use TTS provider
        audio_path = self.tts.synthesize(
            text=full_text,
            voice=voice,
        )
        
        return audio_path
    
    async def _generate_subtitles(
        self,
        audio_path: Path,
        request_id: str,
    ) -> SubtitleResult:
        """Generate subtitles from audio."""
        subtitle_result = self.subtitle_generator.generate_subtitles(
            audio_path=audio_path,
            output_format="srt",  # SRT is more widely supported
        )
        return subtitle_result
    
    async def _generate_images(
        self,
        script: GeneratedScript,
        request: ContentRequest,
        request_id: str,
    ) -> List[Path]:
        """Generate images for video (optional, hardware-gated)."""
        if not self.image_gen:
            logger.warning("Image generation requested but no provider available")
            return []
        
        # Use custom prompts if provided, otherwise derive from script sections
        prompts = request.image_prompts
        if not prompts:
            # Generate image prompts from script sections
            prompts = []
            for section in script.sections:
                if section.visual_note:
                    prompts.append(section.visual_note)
            
            # If no visual notes, create generic prompts from content
            if not prompts:
                prompts = [
                    f"Professional image for social media post about {script.topic}",
                ]
        
        # Generate images
        image_paths: List[Path] = []
        for i, prompt in enumerate(prompts[:5]):  # Limit to 5 images max
            try:
                logger.info(f"Generating image {i+1}/{len(prompts)}: {prompt[:50]}...")
                img_path = self.image_gen.generate(prompt=prompt)
                image_paths.append(img_path)
            except Exception as e:
                logger.warning(f"Failed to generate image {i+1}: {e}")
                # Continue with other images
        
        return image_paths
    
    async def _assemble_video(
        self,
        audio_path: Path,
        subtitle_path: Path,
        image_paths: List[Path],
        background_music: str | None,
        format_type: str,
        request_id: str,
    ) -> PipelineResult:
        """Assemble final video from components."""
        
        # If we have images, create slideshow
        if image_paths:
            # Create slideshow from images matching audio duration
            video_base = self.ffmpeg.create_slideshow(
                image_paths=[str(p) for p in image_paths],
                output_name=f"{request_id}_slideshow.mp4",
            )
            
            # Combine with audio
            video_with_audio = self.ffmpeg.combine_audio_video(
                video_path=Path(video_base.output_path),
                audio_path=audio_path,
                output_name=f"{request_id}_with_audio.mp4",
            )
        else:
            # No images: create a simple black screen video with audio
            # (FFmpeg can do this, but for now we'll use a placeholder approach)
            # In production, you'd generate a simple color background or use stock footage
            logger.warning("No images available, creating audio-only output")
            # For now, just use the audio directly (would need video wrapper in production)
            video_with_audio = PipelineResult(
                output_path=str(audio_path),
                duration=None,
                file_size=audio_path.stat().st_size,
                operations_applied=["audio_only"],
                success=True,
            )
        
        # Add subtitles (burned-in)
        final_video = self.ffmpeg.add_subtitles(
            video_path=Path(video_with_audio.output_path),
            subtitle_path=subtitle_path,
            output_name=f"{request_id}_final.mp4",
        )
        
        # Apply platform preset (resize for Instagram Reel, Post, etc.)
        if format_type in ["reel", "story"]:
            preset_name = "instagram_reel"  # 1080×1920 vertical
        elif format_type == "post":
            preset_name = "instagram_post"  # 1080×1080 square
        else:
            preset_name = "instagram_post"  # default
        
        final_with_preset = self.ffmpeg.apply_preset(
            input_path=Path(final_video.output_path),
            preset_name=preset_name,
            output_name=f"{request_id}_{format_type}_final.mp4",
        )
        
        return final_with_preset
    
    def get_info(self) -> dict:
        """Get pipeline information and capabilities."""
        return {
            "pipeline": "ContentGenerationPipeline",
            "capabilities": {
                "script_generation": True,
                "audio_synthesis": True,
                "subtitle_generation": True,
                "image_generation": self.image_gen is not None,
                "video_assembly": True,
            },
            "supported_formats": ["reel", "post", "story", "carousel"],
            "providers": {
                "tts": self.tts.__class__.__name__,
                "stt": self.stt.__class__.__name__,
                "image_gen": self.image_gen.__class__.__name__ if self.image_gen else None,
            },
        }
