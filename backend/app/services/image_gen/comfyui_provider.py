# backend/app/services/image_gen/comfyui_provider.py
# Cost classification: FREE + OPEN SOURCE (GPL-3.0), LOCAL ONLY
"""
Image generation provider using ComfyUI + Stable Diffusion.

HARDWARE NOTICE:
- CPU only: Works but VERY SLOW (1-5+ min per image with SD 1.5)
- GPU 8GB+: Practical (10-30s per image)
- GPU 12GB+: Comfortable, can run SDXL

LICENSE NOTICE:
- ComfyUI: GPL-3.0 (open source)
- SD 1.5: CreativeML OpenRAIL-M — has use-based restrictions
  (no harmful content generation) but does NOT block commercial use
  for legitimate content creation.
- SDXL: CreativeML OpenRAIL++-M — similar restrictions.

This provider connects to a ComfyUI server via its API.
ComfyUI must be running separately (it's a standalone application).
"""

import logging
import uuid
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Default ComfyUI server
DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"


class ComfyUIImageProvider:
    """
    Image generation via ComfyUI API.
    
    Implements ImageGenProvider protocol.
    Connects to a running ComfyUI instance for image generation.
    
    HARDWARE GATE: On CPU-only / 8GB RAM systems, image generation
    will be extremely slow (1-5+ minutes per image). This is documented
    honestly per ARCHITECTURE.md §4. A GPU with 8GB+ VRAM is strongly
    recommended for practical use.
    """
    
    def __init__(
        self,
        comfyui_url: str = DEFAULT_COMFYUI_URL,
        output_dir: str | Path | None = None,
    ):
        self.comfyui_url = comfyui_url
        self.output_dir = Path(output_dir or settings.STORAGE_ROOT / "generated")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._available = None
    
    def _check_available(self) -> bool:
        """Check if ComfyUI server is running."""
        if self._available is not None:
            return self._available
        
        try:
            import httpx
            response = httpx.get(f"{self.comfyui_url}/system_stats", timeout=5)
            self._available = response.status_code == 200
            if self._available:
                logger.info(f"ComfyUI available at {self.comfyui_url}")
        except Exception:
            self._available = False
            logger.warning(
                f"ComfyUI not available at {self.comfyui_url}. "
                "Start ComfyUI separately to enable image generation."
            )
        
        return self._available
    
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1,
        **kwargs
    ) -> Path:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Positive prompt describing desired image
            negative_prompt: Things to avoid in the image
            width: Image width
            height: Image height
            steps: Inference steps (more = higher quality, slower)
            cfg_scale: Guidance scale
            seed: Random seed (-1 for random)
            **kwargs: Additional ComfyUI parameters
        
        Returns:
            Path to generated image file
        
        Raises:
            RuntimeError: If ComfyUI is not running or generation fails
        """
        if not self._check_available():
            raise RuntimeError(
                "ComfyUI is not running. Image generation requires ComfyUI.\n"
                "1. Install ComfyUI: https://github.com/comfyanonymous/ComfyUI\n"
                "2. Download a model (SD 1.5 or SDXL-Lightning)\n"
                "3. Start ComfyUI: python main.py\n"
                "4. Retry this request\n\n"
                "HARDWARE NOTE: On CPU-only / 8GB RAM, generation will be "
                "very slow (1-5+ min/image). A GPU with 8GB+ VRAM is recommended."
            )
        
        import httpx
        
        # Build ComfyUI workflow (simplified text-to-image)
        workflow = self._build_txt2img_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed,
        )
        
        # Queue the prompt
        client_id = uuid.uuid4().hex[:12]
        response = httpx.post(
            f"{self.comfyui_url}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=300  # 5 min timeout for slow hardware
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"ComfyUI prompt failed: {response.text}")
        
        prompt_id = response.json().get("prompt_id")
        
        # Wait for completion and get output
        output_path = self._wait_and_download(prompt_id, client_id)
        
        logger.info(f"Image generated: {output_path}")
        return output_path
    
    def _build_txt2img_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        seed: int,
    ) -> dict:
        """Build a ComfyUI API workflow for text-to-image."""
        # This is a minimal ComfyUI workflow
        # In practice, users would customize this via ComfyUI's UI
        if seed == -1:
            import random
            seed = random.randint(0, 2**32 - 1)
        
        return {
            "3": {  # KSampler
                "class_type": "KSampler",
                "inputs": {
                    "cfg": cfg_scale,
                    "denoise": 1.0,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": seed,
                    "steps": steps,
                }
            },
            "4": {  # CheckpointLoader
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.safetensors"  # SD 1.5
                }
            },
            "5": {  # EmptyLatentImage
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width,
                }
            },
            "6": {  # CLIPTextEncode (positive)
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt,
                }
            },
            "7": {  # CLIPTextEncode (negative)
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": negative_prompt or "ugly, blurry, low quality",
                }
            },
            "8": {  # VAEDecode
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2],
                }
            },
            "9": {  # SaveImage
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "aism_gen",
                    "images": ["8", 0],
                }
            }
        }
    
    def _wait_and_download(self, prompt_id: str, client_id: str) -> Path:
        """Wait for ComfyUI to finish and download the result."""
        import httpx
        import time
        
        # Poll for completion
        max_wait = 600  # 10 minutes for CPU
        elapsed = 0
        poll_interval = 2
        
        while elapsed < max_wait:
            response = httpx.get(
                f"{self.comfyui_url}/history/{prompt_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    # Find the SaveImage node output
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for img_info in node_output["images"]:
                                filename = img_info["filename"]
                                subfolder = img_info.get("subfolder", "")
                                
                                # Download the image
                                img_response = httpx.get(
                                    f"{self.comfyui_url}/view",
                                    params={
                                        "filename": filename,
                                        "subfolder": subfolder,
                                        "type": "output"
                                    },
                                    timeout=30
                                )
                                
                                if img_response.status_code == 200:
                                    output_path = self.output_dir / f"gen_{uuid.uuid4().hex[:12]}.png"
                                    output_path.write_bytes(img_response.content)
                                    return output_path
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        raise RuntimeError(f"Image generation timed out after {max_wait}s")
    
    def get_info(self) -> dict:
        """Get provider info and status."""
        return {
            "provider": "ComfyUI",
            "available": self._check_available(),
            "url": self.comfyui_url,
            "output_dir": str(self.output_dir),
            "cost": "FREE + OPEN SOURCE (GPL-3.0)",
            "hardware_note": (
                "CPU: Works but slow (1-5+ min/image). "
                "GPU 8GB+: Practical (10-30s). "
                "GPU 12GB+: SDXL capable."
            ),
            "license_note": (
                "SD 1.5: CreativeML OpenRAIL-M — "
                "has use-based restrictions on harmful content, "
                "but allows commercial use for legitimate content creation."
            ),
        }
