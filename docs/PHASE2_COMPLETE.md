# Phase 2: Content Library — Implementation Complete

This document describes the Phase 2 implementation for the AI SEO & Social Media Manager project.

## Overview

Phase 2 adds comprehensive content library functionality with local AI-powered analysis:

- **Upload & Storage**: File upload with organized storage buckets
- **Media Analysis**: FFmpeg-based metadata extraction (duration, dimensions, format)
- **Transcription**: Faster-whisper for audio/video transcription with timestamps
- **Visual Analysis**: CLIP for image embeddings, tags, and scene classification
- **Embeddings**: BGE-small-en-v1.5 for text embeddings
- **Vector Store**: Chroma for RAG and semantic search
- **Thumbnail Generation**: Automated thumbnail creation for images and videos

## Architecture Compliance

✅ **Zero-cost/free-only**: All dependencies are free and open source  
✅ **Provider abstraction**: All AI capabilities behind protocol interfaces  
✅ **Deterministic first**: FFmpeg, PIL, storage logic is pure Python  
✅ **Local-first**: Everything runs locally without external APIs  
✅ **Incremental delivery**: Built on Phase 1 foundation

## New Dependencies

Added to [`backend/requirements.txt`](backend/requirements.txt):

```txt
# Speech-to-text (faster-whisper with CTranslate2)
faster-whisper>=1.0.0

# Embeddings (sentence-transformers with BGE models)
sentence-transformers>=2.2.0

# Vision (OpenCLIP for image embeddings & zero-shot classification)
open_clip_torch>=2.20.0
pillow>=10.0.0

# Vector database (Chroma for RAG)
chromadb>=0.4.0

# Image processing
opencv-python-headless>=4.8.0
```

## File Structure

```
backend/app/services/
├── providers.py                    # Protocol definitions for all AI providers
├── embeddings/
│   ├── __init__.py
│   └── sentence_transformers_provider.py  # BGE embeddings
├── stt/
│   ├── __init__.py
│   └── faster_whisper_provider.py  # Faster-whisper transcription
├── vision/
│   ├── __init__.py
│   └── clip_vision_provider.py     # CLIP vision analysis
├── vector_store/
│   ├── __init__.py
│   └── chroma_store.py             # Chroma vector database
├── media_analysis.py               # FFmpeg-based analysis (Phase 1)
├── storage.py                      # Local file storage (Phase 1)
└── thumbnail.py                    # Thumbnail generation (NEW)

backend/app/api/
└── content.py                      # Extended with new endpoints
```

## API Endpoints

### Existing (Phase 1)

- `POST /content/upload` - Upload media file
- `POST /content/{asset_id}/analyze` - Run FFmpeg analysis

### New (Phase 2)

- `POST /content/{asset_id}/transcribe` - Transcribe audio/video with faster-whisper
- `POST /content/{asset_id}/visual-analysis` - Analyze images with CLIP
- `GET /content/` - List content assets with filtering
- `GET /content/{asset_id}` - Get single asset details

## Provider Protocols

All AI providers implement typed protocols in [`backend/app/services/providers.py`](backend/app/services/providers.py):

- `STTProvider` - Speech-to-text transcription
- `EmbeddingProvider` - Text/image embeddings
- `VisionProvider` - Image analysis and captioning
- `LLMProvider` - Text generation (for Phase 3)
- `TTSProvider` - Text-to-speech (for Phase 5)
- `ImageGenProvider` - Image generation (for Phase 5)
- `VideoGenProvider` - Video generation (for Phase 5)

## Installation & Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Note**: First run will download models automatically:

- faster-whisper: ~140MB (base model)
- sentence-transformers: ~130MB (BGE-small-en-v1.5)
- CLIP: ~350MB (ViT-B-32)

### 2. Configuration

Add to [`backend/.env`](.env):

```env
# Chroma vector database
CHROMA_PERSIST_DIR=../chroma_data

# FFmpeg paths (if not in PATH)
FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe
```

### 3. Verify Installation

Run tests:

```bash
cd backend
pytest tests/content/test_phase2_providers.py -v
```

## Usage Examples

### Transcribe a Video

```bash
# Upload video
curl -X POST http://localhost:8000/content/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "brand_profile_id=$BRAND_ID" \
  -F "file=@video.mp4"

# Transcribe (stores in DB + vector store for RAG)
curl -X POST http://localhost:8000/content/{asset_id}/transcribe \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{
  "asset_id": "...",
  "transcript": "Full transcript text...",
  "language": "en",
  "segments": 15,
  "duration": 45.3
}
```

### Analyze an Image

```bash
# Upload image
curl -X POST http://localhost:8000/content/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "brand_profile_id=$BRAND_ID" \
  -F "file=@photo.jpg"

# Visual analysis (tags, scene type, embedding)
curl -X POST http://localhost:8000/content/{asset_id}/visual-analysis \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{
  "asset_id": "...",
  "tags": ["person", "outdoor scene", "nature", "travel"],
  "scene_type": "outdoor scene",
  "caption": "Image showing: person, outdoor scene, nature, travel"
}
```

### List Content Library

```bash
# List all assets
curl -X GET "http://localhost:8000/content/" \
  -H "Authorization: Bearer $TOKEN"

# Filter by media type
curl -X GET "http://localhost:8000/content/?media_type=video&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

## Vector Store & RAG

All transcripts and visual analyses are automatically stored in Chroma for semantic search:

- **Transcripts**: Full text indexed with embeddings
- **Visual content**: Tag-based text representation with CLIP embeddings
- **Metadata**: Asset ID, brand profile, type, language

Ready for Phase 3 RAG queries.

## Hardware Requirements

### Minimum (CPU-only)

- **RAM**: 4GB available (models load ~1GB total)
- **Storage**: 1GB for models + content storage
- **CPU**: Any modern x64 processor

### Recommended

- **RAM**: 8GB+ (comfortable for concurrent operations)
- **Storage**: 5GB+ (models + content library)
- **CPU**: Multi-core for faster processing

### GPU (Optional)

- Faster-whisper: 2-3x speedup on CUDA GPU
- CLIP: 5-10x speedup on CUDA GPU
- Not required for functionality

## Performance Notes

### Model Load Times (first use)

- Faster-whisper base: ~2-3 seconds
- BGE embeddings: ~1-2 seconds
- CLIP ViT-B-32: ~3-5 seconds

### Processing Times (CPU, approximate)

- **Transcription**: ~1/10th real-time (1 min audio = ~6 sec)
- **Image analysis**: ~2-3 seconds per image
- **Embeddings**: ~50ms per text chunk
- **Thumbnail generation**: <1 second

## Next Steps: Phase 3

With Phase 2 complete, the foundation is ready for Phase 3:

- **LLM Integration**: Ollama with Qwen2.5 for text generation
- **RAG Queries**: Semantic search over content library
- **Content Ideation**: AI-powered content suggestions
- **Caption Generation**: RAG-enhanced caption writing

## Troubleshooting

### "faster-whisper not installed"

```bash
pip install faster-whisper
```

### "FFmpeg not found"

Install FFmpeg:

- **Windows**: Download from ffmpeg.org or use `choco install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux**: `apt install ffmpeg` or `yum install ffmpeg`

### Models downloading slowly

Models download from HuggingFace on first use. Set HF_HOME to cache:

```bash
export HF_HOME=/path/to/cache
```

### Out of memory

Use smaller models:

- Faster-whisper: Use "tiny" or "small" instead of "base"
- Embeddings: Already using BGE-small (smallest recommended)
- CLIP: Already using ViT-B-32 (balanced size/quality)

## Cost Classification Summary

| Component             | Classification                  | Notes      |
| --------------------- | ------------------------------- | ---------- |
| faster-whisper        | FREE + OPEN SOURCE (MIT)        | Local only |
| sentence-transformers | FREE + OPEN SOURCE (Apache 2.0) | Local only |
| CLIP (open_clip)      | FREE + OPEN SOURCE (MIT)        | Local only |
| Chroma                | FREE + OPEN SOURCE (Apache 2.0) | Local only |
| PIL/Pillow            | FREE + OPEN SOURCE (HPND)       | Local only |
| OpenCV                | FREE + OPEN SOURCE (Apache 2.0) | Local only |

**Total recurring cost: $0**
