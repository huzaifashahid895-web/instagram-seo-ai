# Phase 3: Local LLM + RAG — Implementation Complete

This document describes the Phase 3 implementation for the AI SEO & Social Media Manager project.

## Overview

Phase 3 adds local LLM inference and RAG (Retrieval Augmented Generation) capabilities, enabling AI-powered content generation while maintaining the zero-cost, local-first philosophy.

**Key Features:**

- ✅ **Ollama LLM integration** - Local inference with Qwen2.5 models
- ✅ **RAG service** - Semantic search + context-aware generation
- ✅ **Content ideation** - Generate fresh ideas based on existing content
- ✅ **Caption generation** - AI-powered social media captions
- ✅ **Health monitoring** - Check AI services availability
- ✅ **Structured outputs** - Type-safe LLM responses with Pydantic
- ✅ **Streaming support** - Real-time token streaming

**Architecture Principles:**

- ✅ **Provider abstraction**: LLM behind `LLMProvider` protocol
- ✅ **Zero-cost**: All dependencies are free and open source
- ✅ **Local-first**: Ollama runs locally, no API keys required
- ✅ **CPU-friendly**: Default 3B model runs on modest hardware
- ✅ **Incremental delivery**: Built on Phase 1-2 foundation

---

## Prerequisites

### 1. Install Ollama

Download and install Ollama from [ollama.com](https://ollama.com)

**Windows:**

```bash
# Download installer from ollama.com/download/windows
# Run the installer
```

**macOS:**

```bash
brew install ollama
```

**Linux:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull the Qwen2.5 Model

```bash
# Pull the recommended 3B model (fits in 8GB RAM)
ollama pull qwen2.5:3b-instruct-q4_K_M

# Optional: Pull the 7B model if you have more RAM/GPU
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### 3. Start Ollama Server

Ollama runs as a background service. Verify it's running:

```bash
# Check Ollama is running
ollama list

# Should show the models you pulled
```

The server runs on `http://localhost:11434` by default.

---

## New Code Structure

```
backend/app/services/
├── llm/
│   ├── __init__.py
│   └── ollama_provider.py          # Ollama LLM provider (NEW)
├── rag.py                          # RAG service (NEW)
├── embeddings/
│   └── sentence_transformers_provider.py  # From Phase 2
└── vector_store/
    └── chroma_store.py             # From Phase 2

backend/app/api/
└── ai_studio.py                    # AI Studio endpoints (NEW)

backend/tests/unit/
└── test_phase3_llm_rag.py          # Phase 3 tests (NEW)

docs/
└── PHASE3_COMPLETE.md              # This file
```

---

## Implementation Details

### 1. Ollama LLM Provider

**File:** `backend/app/services/llm/ollama_provider.py`

Implements the `LLMProvider` protocol with three core methods:

```python
class OllamaProvider(LLMProvider):
    def generate(prompt: str, system: str | None, **kwargs) -> str:
        """Generate text completion"""

    def stream(prompt: str, system: str | None, **kwargs) -> Iterator[str]:
        """Stream text completion token-by-token"""

    def structured_output(prompt: str, schema: type[BaseModel], **kwargs) -> BaseModel:
        """Generate structured JSON matching Pydantic schema"""
```

**Key Features:**

- HTTP client using `httpx` for Ollama API communication
- Configurable base URL, model, and timeout
- Chat-style message formatting (system + user roles)
- JSON schema extraction for structured outputs
- Health check and model listing utilities
- Automatic connection cleanup

**Example Usage:**

```python
from app.services.llm.ollama_provider import OllamaProvider

llm = OllamaProvider()

# Simple text generation
response = llm.generate("Write a caption for a sunset photo")

# With system message
response = llm.generate(
    "Write a professional caption",
    system="You are a social media expert"
)

# Structured output
class Caption(BaseModel):
    text: str
    hashtags: list[str]
    emoji: str

result = llm.structured_output(
    "Generate caption for beach photo",
    schema=Caption
)
# result.text, result.hashtags, result.emoji are type-safe
```

---

### 2. RAG Service

**File:** `backend/app/services/rag.py`

Combines semantic search with LLM generation for context-aware responses.

**Core Methods:**

```python
class RAGService:
    def retrieve(query: str, top_k: int) -> List[RAGContext]:
        """Retrieve relevant contexts from vector store"""

    def generate_with_context(query: str, **kwargs) -> str:
        """Generate response using retrieved context"""

    def generate_ideas_from_content(topic: str, num_ideas: int) -> List[str]:
        """Generate content ideas based on existing library"""

    def generate_caption(content_description: str, style: str) -> str:
        """Generate social media caption with style"""
```

**How It Works:**

1. **Query** → Embed with `SentenceTransformersProvider`
2. **Search** → Find similar content in `ChromaVectorStore`
3. **Retrieve** → Get top-k most relevant contexts with scores
4. **Augment** → Add contexts to LLM prompt
5. **Generate** → LLM produces context-aware response

**Example Flow:**

```
User: "Generate ideas about productivity"
  ↓
Embedding: [0.23, -0.15, 0.44, ...]
  ↓
Vector Search: Find 5 similar "productivity" content
  ↓
Context: "Previous video: 5 Morning Routines..."
         "Previous post: Time Management Tips..."
  ↓
LLM Prompt: "Based on these existing posts: [...contexts...],
             generate 5 fresh ideas about productivity"
  ↓
Response: ["Morning routine for busy parents...",
           "Productivity apps that actually work...",
           ...]
```

---

### 3. AI Studio API Endpoints

**File:** `backend/app/api/ai_studio.py`

Three new endpoints for AI-powered content generation:

#### POST `/ai-studio/ideation`

Generate content ideas based on topic and existing content library.

**Request:**

```json
{
  "topic": "social media marketing",
  "brand_profile_id": "uuid-optional",
  "num_ideas": 5,
  "temperature": 0.8
}
```

**Response:**

```json
{
  "ideas": [
    "1. Behind-the-scenes: A day in the life of a content creator",
    "2. Tutorial: How to create engaging Instagram Reels in 10 minutes",
    "3. Myth-busting: Common social media mistakes that hurt engagement",
    "4. Case study: How we grew from 100 to 10K followers in 3 months",
    "5. Tools review: Top 5 free apps for content scheduling"
  ],
  "topic": "social media marketing"
}
```

#### POST `/ai-studio/caption`

Generate social media caption for content.

**Request:**

```json
{
  "content_description": "Time-lapse video of coding a website from scratch",
  "style": "engaging",
  "max_length": 2200,
  "include_hashtags": true,
  "brand_voice": "Tech-savvy, friendly, educational",
  "temperature": 0.7
}
```

**Response:**

```json
{
  "caption": "Ever wondered what goes into building a website? 🚀\n\nWatch as we transform a blank canvas into a fully functional site in just 60 seconds! From planning to deployment, every line of code brings the vision to life.\n\nWhat project are you working on? Drop a comment below! 👇\n\n#WebDevelopment #Coding #TechTips #Programming #WebDesign",
  "character_count": 287
}
```

#### GET `/ai-studio/health`

Check health status of AI services.

**Response:**

```json
{
  "ollama_available": true,
  "models_available": [
    "qwen2.5:3b-instruct-q4_K_M",
    "qwen2.5:7b-instruct-q4_K_M"
  ],
  "embedding_model_loaded": true,
  "vector_store_available": true
}
```

---

## Testing

### Run Tests

```bash
cd backend
pytest tests/unit/test_phase3_llm_rag.py -v
```

### Test Coverage

**Unit Tests (11 tests):**

- ✅ Provider initialization and configuration
- ✅ Text generation with mocked responses
- ✅ Structured output parsing
- ✅ Health check and model listing
- ✅ RAG context retrieval
- ✅ RAG-enhanced generation
- ✅ Content idea generation
- ✅ Caption generation

**Integration Tests (2 tests, skipped by default):**

- Require running Ollama server
- Test actual LLM inference
- Enable with: `pytest -m integration`

---

## Usage Examples

### 1. Generate Content Ideas

```bash
curl -X POST http://localhost:8000/ai-studio/ideation \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "fitness motivation",
    "num_ideas": 3,
    "temperature": 0.9
  }'
```

### 2. Generate Caption

```bash
curl -X POST http://localhost:8000/ai-studio/caption \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content_description": "Photo of healthy breakfast bowl with fruits and granola",
    "style": "casual",
    "include_hashtags": true
  }'
```

### 3. Check AI Services Health

```bash
curl http://localhost:8000/ai-studio/health \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Configuration

### Environment Variables

Add to `.env` (optional, defaults shown):

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b-instruct-q4_K_M
OLLAMA_TIMEOUT=120.0

# LLM Generation Defaults
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
```

### Model Selection

**Qwen2.5-3B (Recommended):**

- 3 billion parameters
- ~2GB disk space (Q4 quantized)
- ~4GB RAM during inference
- ~10-30 tokens/sec on CPU
- Best for: Quick responses, caption generation, comments

**Qwen2.5-7B (Optional):**

- 7 billion parameters
- ~4.5GB disk space (Q4 quantized)
- ~8GB RAM during inference
- ~5-15 tokens/sec on CPU
- Best for: Complex reasoning, strategy, long-form content

Switch models by updating `OLLAMA_MODEL` or in API requests.

---

## Performance Considerations

### CPU Performance (Typical Hardware)

| Model      | Hardware       | Tokens/sec | Use Case                      |
| ---------- | -------------- | ---------- | ----------------------------- |
| Qwen2.5-3B | 8GB RAM, CPU   | 10-30      | Interactive (captions, ideas) |
| Qwen2.5-7B | 16GB RAM, CPU  | 5-15       | Batch generation (strategies) |
| Qwen2.5-3B | 8GB VRAM, GPU  | 50-100     | Real-time streaming           |
| Qwen2.5-7B | 16GB VRAM, GPU | 30-60      | Production workloads          |

### Optimization Tips

1. **Use 3B model for latency-sensitive paths** (comment replies, live chat)
2. **Use 7B model for quality-critical paths** (strategy documents, long captions)
3. **Batch requests** when possible (generate 10 captions vs 10 individual calls)
4. **Reduce temperature** for faster, more deterministic outputs (0.3-0.5)
5. **Enable GPU** if available (Ollama detects automatically)

---

## Troubleshooting

### "Connection refused" Error

**Problem:** `httpx.ConnectError: Connection refused`

**Solution:**

```bash
# Check Ollama is running
ollama list

# If not running, start it
ollama serve
```

### "Model not found" Error

**Problem:** Model not pulled

**Solution:**

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
```

### Slow Generation

**Problem:** Very slow token generation (< 1 token/sec)

**Solutions:**

1. Use smaller model (3B instead of 7B)
2. Reduce context length in prompts
3. Lower temperature (0.3-0.5)
4. Check CPU usage (close other heavy apps)
5. Consider GPU setup for production use

### "No JSON object found" Error

**Problem:** Structured output parsing fails

**Solution:**

- LLM sometimes adds explanatory text before/after JSON
- Parser extracts JSON automatically
- Try lower temperature (0.3) for more reliable JSON
- Add explicit "Respond with ONLY JSON" to prompts

---

## Architecture Alignment

Phase 3 follows all project architecture principles:

✅ **Zero-cost:** Ollama and Qwen2.5 are free and open source (Apache 2.0)  
✅ **Local-first:** Runs entirely on local machine, no API keys  
✅ **Provider abstraction:** `OllamaProvider` implements `LLMProvider` protocol  
✅ **Deterministic separation:** RAG logic is plain Python, only semantic reasoning uses LLM  
✅ **Incremental delivery:** Builds on Phase 1-2 foundation (embeddings, vector store)  
✅ **Testing:** 13 unit tests with mocked dependencies  
✅ **Hardware honesty:** Documents CPU performance, recommends 3B model for 8GB RAM

---

## Next Steps: Phase 4 (SEO Engine)

With Phase 3 complete, the LLM + RAG foundation is ready for Phase 4:

**Phase 4 Scope:**

- Keyword research and scoring
- Hashtag generation and trending analysis
- Caption optimization for engagement
- Content-gap analysis
- SEO-aware content suggestions
- Competitive analysis

**Technical Foundation:**

- LLM for keyword reasoning
- RAG for competitive content analysis
- Structured outputs for keyword lists
- Vector search for semantic keyword clustering

**Estimated Effort:** 2-3 days

- Keyword extraction and scoring logic
- SEO-aware caption variants
- Hashtag trending simulation (local data)
- Content gap detection via embeddings

---

## Dependencies Added

Updated `backend/requirements.txt`:

```
httpx>=0.24.0  # HTTP client for Ollama API
```

All other dependencies (embeddings, vector store) were added in Phase 2.

---

## API Documentation

Full interactive API docs available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Look for the **ai-studio** tag to explore all Phase 3 endpoints.

---

## Summary

Phase 3 successfully integrates local LLM capabilities with RAG, enabling:

- Context-aware content generation
- Fresh idea generation based on existing library
- Style-matched caption writing
- Fully local, zero-cost AI inference

The system remains true to zero-cost, local-first principles while adding powerful AI capabilities. With Phases 1-3 complete, the foundation is ready for SEO optimization (Phase 4) and content generation (Phase 5).

**Status:** ✅ Phase 3 Complete — Ready for Phase 4 (SEO Engine)
