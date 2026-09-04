# GPU Features Setup Guide

This guide covers setting up AI image generation (Stable Diffusion) and video generation for the Instagram SEO & Social Media Manager.

## ⚠️ Hardware Requirements

### Minimum for Image Generation (Stable Diffusion):

- **GPU**: NVIDIA GPU with 6GB+ VRAM
- **RAM**: 16GB system RAM
- **Storage**: 10GB+ free space
- **OS**: Windows 10/11, Linux, or macOS (Apple Silicon)

### Minimum for Video Generation:

- **GPU**: NVIDIA GPU with 12GB+ VRAM (24GB recommended)
- **RAM**: 32GB+ system RAM
- **Storage**: 50GB+ free space for models

### CPU-Only Alternative:

- ⚠️ **Not recommended** - 50-100x slower
- Image generation: 2-5 minutes per image
- Video generation: Not practical (hours per video)

---

## Part 1: Check Your GPU

### Windows

```cmd
# Check if you have NVIDIA GPU:
nvidia-smi
```

If you see GPU information, continue. If not, you need a GPU.

### Verify CUDA Support

```cmd
# Check CUDA version:
nvcc --version
```

If not found, install CUDA Toolkit: https://developer.nvidia.com/cuda-downloads

---

## Part 2: Image Generation (Stable Diffusion)

### Option A: ComfyUI (Recommended)

ComfyUI is a node-based UI for Stable Diffusion with excellent model management.

#### Step 1: Install ComfyUI

```cmd
# Clone ComfyUI:
cd "C:\AI"
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install dependencies:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

#### Step 2: Download Models

Download Stable Diffusion models to `ComfyUI\models\checkpoints\`:

**SDXL-Lightning (Fast, good quality):**

```cmd
# Download from: https://huggingface.co/ByteDance/SDXL-Lightning
# Place in: ComfyUI\models\checkpoints\sdxl_lightning_4step.safetensors
```

**SD 1.5 (Smaller, faster on lower VRAM):**

```cmd
# Download from: https://huggingface.co/runwayml/stable-diffusion-v1-5
# Place in: ComfyUI\models\checkpoints\v1-5-pruned.safetensors
```

#### Step 3: Start ComfyUI

```cmd
cd "C:\AI\ComfyUI"
python main.py --listen 0.0.0.0 --port 8188
```

Access: http://localhost:8188

#### Step 4: Test Image Generation

1. Load a workflow in ComfyUI
2. Enter prompt: "Instagram post about coffee, aesthetic, professional"
3. Click "Queue Prompt"
4. Wait ~5-10 seconds for image

#### Step 5: Integrate with App

Install ComfyUI API client:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install websocket-client==1.7.0
```

Create `backend/app/services/image_gen/comfyui_provider.py`:

```python
import json
import requests
import websocket
from app.services.image_gen import ImageGenProvider

class ComfyUIProvider(ImageGenProvider):
    def __init__(self, base_url: str = "http://localhost:8188"):
        self.base_url = base_url
        self.client_id = "aism"

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate image and return file path."""
        # Load workflow
        workflow = self._load_workflow()

        # Update prompt
        workflow["6"]["inputs"]["text"] = prompt

        # Queue prompt
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": self.client_id}
        )
        prompt_id = response.json()["prompt_id"]

        # Wait for completion via WebSocket
        image_path = self._wait_for_image(prompt_id)
        return image_path

    def _load_workflow(self):
        # Load your ComfyUI workflow JSON
        with open("workflows/txt2img.json") as f:
            return json.load(f)

    def _wait_for_image(self, prompt_id: str) -> str:
        # WebSocket logic to wait for image
        # Return path to generated image
        pass
```

Update `.env`:

```env
COMFYUI_URL=http://localhost:8188
IMAGE_GEN_PROVIDER=comfyui
```

---

### Option B: Automatic1111 WebUI

Alternative to ComfyUI with different UI.

#### Install

```cmd
cd "C:\AI"
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui
webui-user.bat
```

First run downloads models automatically.

Access: http://localhost:7860

---

## Part 3: Video Generation

### ⚠️ Reality Check

Current state of open-source video generation:

- **CogVideoX** - 24GB VRAM minimum, ~5 min per 5sec video
- **Wan2.1** - Similar requirements, experimental quality
- **LTX-Video** - Newer, requires 20GB+ VRAM

**Recommendation:** Wait for better models or use cloud APIs until you have appropriate hardware.

---

### Option A: Cloud API (Practical Solution)

Since local video generation needs serious GPU power, consider:

1. **Replicate** (pay-per-use, no subscription)
2. **RunPod** (rent GPU by the minute)
3. **Modal** (serverless GPU)

#### Example: Replicate Integration

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install replicate==0.25.0
```

Get API key: https://replicate.com/account/api-tokens

Update `.env`:

```env
REPLICATE_API_TOKEN=your_token_here
VIDEO_GEN_PROVIDER=replicate
```

Create `backend/app/services/video_gen/replicate_provider.py`:

```python
import replicate
from app.services.video_gen import VideoGenProvider

class ReplicateProvider(VideoGenProvider):
    def generate(self, prompt: str, duration: int = 5, **kwargs) -> str:
        """Generate video via Replicate API."""
        output = replicate.run(
            "cjwbw/text2video-zero:0a3097d5ad7c0bdd5c9d8c7a109f1fca4db3e0b55eb4ec2c0a74bdc38a0f01fc",
            input={
                "prompt": prompt,
                "video_length": duration,
            }
        )

        # Download video
        video_url = output
        local_path = self._download_video(video_url)
        return local_path
```

**Cost:** ~$0.01-0.10 per video depending on length.

---

### Option B: Local Video Generation (Advanced)

Only proceed if you have 24GB+ VRAM.

#### Step 1: Install Dependencies

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install diffusers==0.26.3 transformers==4.38.1 accelerate==0.27.2
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

#### Step 2: Download CogVideoX Model

```python
# This downloads ~20GB:
from diffusers import CogVideoXPipeline

pipe = CogVideoXPipeline.from_pretrained(
    "THUDM/CogVideoX-2b",
    torch_dtype=torch.float16
)
pipe.save_pretrained("./models/cogvideox")
```

#### Step 3: Test Generation

```python
import torch
from diffusers import CogVideoXPipeline

pipe = CogVideoXPipeline.from_pretrained(
    "./models/cogvideox",
    torch_dtype=torch.float16
).to("cuda")

prompt = "A coffee cup on a wooden table, cinematic lighting"
video = pipe(prompt, num_frames=48).frames

# Save video
import imageio
imageio.mimsave("output.mp4", video, fps=8)
```

**Time:** ~3-5 minutes per 6-second video on RTX 4090.

#### Step 4: Integrate with App

Create `backend/app/services/video_gen/cogvideox_provider.py`:

```python
import torch
from diffusers import CogVideoXPipeline
from app.services.video_gen import VideoGenProvider

class CogVideoXProvider(VideoGenProvider):
    def __init__(self):
        self.pipe = CogVideoXPipeline.from_pretrained(
            "./models/cogvideox",
            torch_dtype=torch.float16
        ).to("cuda")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate video locally."""
        video = self.pipe(prompt, num_frames=48).frames

        # Save to storage
        output_path = f"generated/video_{timestamp()}.mp4"
        self._save_video(video, output_path)
        return output_path
```

---

## Part 4: Configuration

### Update App Configuration

Edit `.env`:

```env
# Image Generation
IMAGE_GEN_ENABLED=true
IMAGE_GEN_PROVIDER=comfyui  # Options: comfyui, automatic1111, replicate
COMFYUI_URL=http://localhost:8188

# Video Generation
VIDEO_GEN_ENABLED=true
VIDEO_GEN_PROVIDER=replicate  # Options: cogvideox, replicate, stub
REPLICATE_API_TOKEN=your_token_here

# GPU Settings
CUDA_VISIBLE_DEVICES=0  # Use GPU 0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### Model Selection Config

In Settings page, add model configs:

```json
{
  "name": "SDXL Lightning",
  "type": "image_gen",
  "provider": "comfyui",
  "model_path": "sdxl_lightning_4step.safetensors",
  "settings": {
    "steps": 4,
    "cfg_scale": 1.0,
    "sampler": "euler_a"
  }
}
```

---

## Part 5: Memory Management

### Optimize VRAM Usage

```python
# In your provider initialization:

# Enable attention slicing (saves VRAM)
pipe.enable_attention_slicing()

# Enable VAE slicing
pipe.enable_vae_slicing()

# Enable xformers (faster, less VRAM)
pipe.enable_xformers_memory_efficient_attention()

# Offload to CPU when not in use
pipe.enable_model_cpu_offload()
```

### Monitor GPU Usage

```cmd
# Watch GPU usage:
nvidia-smi -l 1
```

---

## Part 6: Quality vs Speed Tradeoffs

### Image Generation

**Fast (5-10 sec, lower quality):**

- SDXL-Lightning 4-step
- SD 1.5 with LCM

**Quality (30-60 sec):**

- SDXL base with 30-50 steps
- SD 1.5 with 50-80 steps

### Video Generation

**Fast (2-3 min, experimental):**

- AnimateDiff with SD 1.5
- Zeroscope v2

**Quality (5-10 min, better):**

- CogVideoX
- VideoCrafter2

---

## Part 7: Workflow Integration

### In the App UI

1. Go to **AI Studio** page
2. Select "Generate Image" tab
3. Enter prompt: "Professional Instagram post about [topic]"
4. Select style preset
5. Click "Generate"
6. Wait for generation
7. Preview and download

### Batch Generation

```python
# Generate multiple variations:
prompts = [
    "Coffee cup on wooden table, morning light",
    "Coffee beans close-up, professional photography",
    "Latte art heart shape, top view"
]

for prompt in prompts:
    image_path = image_gen_provider.generate(prompt)
    save_to_content_library(image_path)
```

---

## Part 8: Cost Analysis

### Local Generation (One-time costs):

- GPU: $500-2000 (RTX 4070-4090)
- Electricity: ~$0.10-0.30 per hour
- **Total per image:** ~$0.001 (electricity only)
- **Total per video:** ~$0.01 (electricity only)

### Cloud Generation (Pay-per-use):

- Image: $0.002-0.01 per image
- Video: $0.05-0.20 per video (5-10 seconds)

**Break-even:** ~1000-2000 generations

---

## Part 9: Limitations & Warnings

### Content Policy

Stable Diffusion models have built-in safety filters. Don't try to:

- Generate NSFW content
- Create deepfakes
- Violate copyright
- Generate misleading content

### Legal Considerations

- Generated content may not be copyrightable
- Check terms of service for commercial use
- Credit AI generation when appropriate

### Technical Limitations

- GPU memory errors → Reduce resolution or batch size
- Slow generation → Normal for CPU, need GPU
- Poor quality → Adjust prompt, steps, or model

---

## Troubleshooting

### CUDA Out of Memory

```python
# Reduce resolution:
width = 512  # Instead of 1024
height = 512

# Enable memory optimizations
pipe.enable_attention_slicing()
pipe.enable_vae_slicing()

# Use float16 instead of float32
pipe = pipe.to(torch_dtype=torch.float16)
```

### Slow Generation

- Use faster models (SDXL-Lightning, LCM)
- Reduce steps (4-8 instead of 50)
- Lower resolution (512x512 instead of 1024x1024)
- Check GPU utilization with `nvidia-smi`

### Poor Image Quality

- Increase steps (20-50)
- Improve prompt (be specific, add quality tags)
- Use better model (SDXL instead of SD 1.5)
- Adjust CFG scale (7-9 is good range)

---

## Alternative: Hybrid Approach

**Recommended for most users:**

1. Use local image generation (ComfyUI/SD)
2. Use cloud API for video generation (Replicate)
3. Best balance of cost and quality

This gives you:

- ✅ Fast local image generation
- ✅ High-quality video from cloud
- ✅ Reasonable costs (~$10-50/month)
- ✅ No GPU requirement for videos

---

## Summary

### Can Do Now (No GPU):

- ✅ All text features (LLM, embeddings)
- ✅ Audio transcription (Whisper CPU)
- ✅ Cloud image generation (APIs)
- ✅ Cloud video generation (APIs)

### Need GPU For:

- Local fast image generation (6GB+ VRAM)
- Local video generation (24GB+ VRAM)
- Real-time inference
- Cost savings at scale

### Recommendation:

1. Start with cloud APIs for image/video
2. Evaluate usage and costs
3. Invest in GPU if generating >1000 images/month
4. For video, cloud is more practical for now

---

Your GPU features are now configured based on your hardware!
