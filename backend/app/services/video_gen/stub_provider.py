# backend/app/services/video_gen/stub_provider.py
"""
Stub video generation provider with hardware warnings.

Cost classification: REQUIRES GPU + REQUIRES PAID SERVICE (most models)
Hardware requirements: CUDA-capable GPU with 10GB+ VRAM recommended
License: Varies by model (check before use)

AI video generation is computationally intensive and typically requires:
- GPU with 10GB+ VRAM (24GB+ recommended for higher quality)
- 5-30+ minutes per video on consumer hardware
- Significant storage for model weights (10-50GB+ per model)

Popular options (all require substantial GPU resources):
- Stable Video Diffusion (SVD) - GPL-3.0, requires 10GB+ VRAM
- AnimateDiff - Apache-2.0, requires 12GB+ VRAM
- ModelScope T2V - CreativeML OpenRAIL-M, requires 16GB+ VRAM
- Zeroscope - CreativeML OpenRAIL-M, requires 10GB+ VRAM

This stub provider raises descriptive errors rather than attempting
generation on inadequate hardware. Actual implementation should:
1. Check GPU availability and VRAM
2. Verify model license compatibility with commercial use
3. Provide accurate time estimates based on hardware
4. Support multiple backends (ComfyUI, Diffusers, API services)
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StubVideoGenProvider:
    """
    Stub video generation provider.
    
    Raises NotImplementedError with hardware guidance when called.
    Replace this with a real implementation once you have:
    - CUDA-capable GPU with 10GB+ VRAM
    - Verified model license allows your use case
    - Selected specific model/framework to integrate
    """

    def __init__(self):
        """Initialize stub provider."""
        logger.warning(
            "StubVideoGenProvider initialized. This is a placeholder that will "
            "raise NotImplementedError on generate() calls. AI video generation "
            "requires GPU hardware not available on this system."
        )

    def generate(
        self,
        prompt: str,
        duration: float = 3.0,
        fps: int = 8,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 25,
        guidance_scale: float = 9.0,
        seed: int | None = None,
        output_path: str | Path | None = None,
        **kwargs,
    ) -> Path:
        """
        Stub video generation method.
        
        Args:
            prompt: Text description of the video to generate
            duration: Video duration in seconds (longer = more VRAM)
            fps: Frames per second (higher = more VRAM + time)
            width: Video width in pixels (must be multiple of 8)
            height: Video height in pixels (must be multiple of 8)
            num_inference_steps: Quality vs speed tradeoff (25-50 typical)
            guidance_scale: How strictly to follow prompt (7.0-12.0 typical)
            seed: Random seed for reproducibility
            output_path: Where to save generated video (MP4)
            **kwargs: Model-specific parameters
            
        Returns:
            Path: Path to generated video file
            
        Raises:
            NotImplementedError: Always, with hardware guidance
        """
        raise NotImplementedError(
            "AI video generation is not available on this system.\n\n"
            "HARDWARE REQUIREMENTS:\n"
            "- CUDA-capable GPU with 10GB+ VRAM (24GB+ recommended)\n"
            "- 5-30+ minutes generation time per short video\n"
            "- 10-50GB+ storage for model weights\n\n"
            "RECOMMENDED ALTERNATIVES:\n"
            "1. Use FFmpeg slideshow creation (already implemented in FFmpegPipeline)\n"
            "   - Combine static images with pan/zoom effects\n"
            "   - Add audio, subtitles, transitions\n"
            "   - Near-instant generation, no GPU required\n"
            "2. Use stock video footage from free sources\n"
            "   - Pexels, Pixabay, Videvo (all free for commercial use)\n"
            "   - Edit with FFmpeg to match your script\n"
            "3. Use simple animation tools\n"
            "   - Ken Burns effect on images (FFmpeg can do this)\n"
            "   - Text overlays and transitions\n\n"
            "FUTURE GPU-BASED IMPLEMENTATION OPTIONS:\n"
            "- Stable Video Diffusion via ComfyUI (GPL-3.0)\n"
            "- AnimateDiff via Diffusers (Apache-2.0)\n"
            "- ModelScope T2V (CreativeML OpenRAIL-M, check license)\n"
            "- Zeroscope (CreativeML OpenRAIL-M, check license)\n\n"
            "If you have GPU hardware available, this stub can be replaced with\n"
            "a real implementation following the VideoGenProvider protocol."
        )

    def get_info(self) -> dict:
        """
        Get provider information and capabilities.
        
        Returns:
            dict: Provider metadata
        """
        return {
            "provider": "StubVideoGenProvider",
            "status": "not_implemented",
            "reason": "requires_gpu",
            "hardware_requirements": {
                "gpu": "CUDA-capable with 10GB+ VRAM",
                "storage": "10-50GB+ for model weights",
                "generation_time": "5-30+ minutes per video",
            },
            "alternatives": [
                "FFmpeg slideshow creation (already available)",
                "Stock video footage editing",
                "Simple animation with Ken Burns effects",
            ],
            "future_options": [
                "Stable Video Diffusion (SVD)",
                "AnimateDiff",
                "ModelScope Text-to-Video",
                "Zeroscope",
            ],
        }

    def check_available(self) -> bool:
        """
        Check if video generation is available.
        
        Returns:
            bool: Always False for stub implementation
        """
        return False
