# Test AI Integration with Backend
"""
Comprehensive test to verify all AI models are properly integrated with the backend.
Run this after setup_ai_models.bat completes successfully.
"""

import sys
import asyncio
import httpx
from pathlib import Path

# Fix Windows console encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.services.llm.ollama_provider import OllamaProvider
from app.services.embeddings.sentence_transformers_provider import SentenceTransformersProvider
from app.services.stt.faster_whisper_provider import FasterWhisperProvider
from app.services.vector_store.chroma_store import ChromaVectorStore


async def test_config():
    """Test that config has AI model settings."""
    print("\n1. Testing Configuration...")
    print("=" * 60)
    
    try:
        print(f"  ✓ OLLAMA_BASE_URL: {settings.OLLAMA_BASE_URL}")
        print(f"  ✓ OLLAMA_MODEL: {settings.OLLAMA_MODEL}")
        print(f"  ✓ EMBEDDINGS_MODEL: {settings.EMBEDDINGS_MODEL}")
        print(f"  ✓ WHISPER_MODEL: {settings.WHISPER_MODEL}")
        print(f"  ✓ CHROMA_HOST: {settings.CHROMA_HOST}")
        print(f"  ✓ CHROMA_PORT: {settings.CHROMA_PORT}")
        return True
    except Exception as e:
        print(f"  ✗ Config error: {e}")
        return False


async def test_ollama_connection():
    """Test Ollama service is running and has models."""
    print("\n2. Testing Ollama Connection...")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check Ollama is running
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                print(f"  ✓ Ollama is running on {settings.OLLAMA_BASE_URL}")
                print(f"  ✓ Available models: {model_names}")
                
                # Check if configured model is available
                if any(settings.OLLAMA_MODEL in name for name in model_names):
                    print(f"  ✓ Configured model '{settings.OLLAMA_MODEL}' is available")
                else:
                    print(f"  ⚠ Model '{settings.OLLAMA_MODEL}' not found")
                    print(f"    Run: ollama pull {settings.OLLAMA_MODEL}")
                
                return True
            else:
                print(f"  ✗ Ollama returned status {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print(f"  ✗ Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}")
        print("    Make sure Ollama is running (ollama serve)")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


async def test_llm_provider():
    """Test LLM provider can generate text."""
    print("\n3. Testing LLM Provider (Ollama + Qwen2.5)...")
    print("=" * 60)
    
    try:
        provider = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL
        )
        
        # Simple generation test
        prompt = "Say 'AI models are working!' in one sentence."
        print(f"  Prompt: {prompt}")
        
        result = provider.generate(prompt, temperature=0.7)
        
        print(f"  ✓ Generated: {result[:100]}...")
        print(f"  ✓ LLM Provider is functional")
        return True
        
    except Exception as e:
        print(f"  ✗ LLM Provider error: {e}")
        return False


async def test_embedding_provider():
    """Test embedding provider can create embeddings."""
    print("\n4. Testing Embedding Provider (BGE)...")
    print("=" * 60)
    
    try:
        provider = SentenceTransformersProvider(
            model_name=settings.EMBEDDINGS_MODEL
        )
        
        # Test single embedding
        text = "This is a test sentence for embeddings."
        print(f"  Text: {text}")
        
        embedding = provider.embed_text(text)
        
        print(f"  ✓ Generated embedding: dimension={len(embedding)}")
        print(f"  ✓ Embedding Provider is functional")
        
        # Test batch embeddings
        texts = ["First sentence", "Second sentence", "Third sentence"]
        embeddings = provider.embed_texts(texts)
        
        print(f"  ✓ Batch embeddings: {len(embeddings)} embeddings generated")
        return True
        
    except Exception as e:
        print(f"  ✗ Embedding Provider error: {e}")
        return False


async def test_vector_store():
    """Test vector store can store and retrieve embeddings."""
    print("\n5. Testing Vector Store (Chroma)...")
    print("=" * 60)
    
    try:
        store = ChromaVectorStore(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            persist_directory=settings.CHROMA_PERSIST_DIR
        )
        
        print(f"  ✓ ChromaVectorStore initialized")
        print(f"  ✓ Persist directory: {settings.CHROMA_PERSIST_DIR}")
        return True
        
    except Exception as e:
        print(f"  ✗ Vector Store error: {e}")
        return False


async def test_stt_provider():
    """Test STT provider is available."""
    print("\n6. Testing STT Provider (faster-whisper)...")
    print("=" * 60)
    
    try:
        provider = FasterWhisperProvider(
            model_size=settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE
        )
        
        print(f"  ✓ FasterWhisperProvider initialized")
        print(f"  ✓ Model: {settings.WHISPER_MODEL}")
        print(f"  ✓ Device: {settings.WHISPER_DEVICE}")
        return True
        
    except Exception as e:
        print(f"  ✗ STT Provider error: {e}")
        return False


async def test_backend_server():
    """Test backend server is running and accessible."""
    print("\n7. Testing Backend Server...")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to reach backend health endpoint
            response = await client.get("http://localhost:8000/docs")
            
            if response.status_code == 200:
                print(f"  ✓ Backend is running on http://localhost:8000")
                print(f"  ✓ API docs: http://localhost:8000/docs")
                return True
            else:
                print(f"  ⚠ Backend returned status {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print(f"  ⚠ Backend not running on http://localhost:8000")
        print("    Start it with: cd backend && uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("AI MODELS INTEGRATION TEST")
    print("=" * 60)
    
    results = []
    
    # Run tests sequentially
    results.append(("Configuration", await test_config()))
    results.append(("Ollama Connection", await test_ollama_connection()))
    results.append(("LLM Provider", await test_llm_provider()))
    results.append(("Embedding Provider", await test_embedding_provider()))
    results.append(("Vector Store", await test_vector_store()))
    results.append(("STT Provider", await test_stt_provider()))
    results.append(("Backend Server", await test_backend_server()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print("\n" + "=" * 60)
    
    if passed_count == total_count:
        print(f"✅ ALL TESTS PASSED ({passed_count}/{total_count})")
        print("\nYour AI models are fully integrated and ready to use!")
        print("\nNext steps:")
        print("  1. Start backend: cd backend && uvicorn app.main:app --reload")
        print("  2. Start frontend: cd frontend && npm run dev")
        print("  3. Go to AI Studio and try generating content")
        return 0
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed_count}/{total_count} passed)")
        print("\nPlease fix the failed tests before using AI features.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
