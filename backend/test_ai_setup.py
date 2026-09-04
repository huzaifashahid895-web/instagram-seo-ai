# Test AI Models Setup
import sys
import asyncio

async def test_ollama():
    """Test Ollama connection."""
    try:
        import httpx
        response = await httpx.AsyncClient().get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama: Connected. Models: {[m['name'] for m in models]}")
            return True
        else:
            print(f"❌ Ollama: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama: {e}")
        return False

async def test_chroma():
    """Test Chroma installation."""
    try:
        import chromadb
        print(f"✅ Chroma: v{chromadb.__version__}")
        return True
    except Exception as e:
        print(f"❌ Chroma: {e}")
        return False

async def test_embeddings():
    """Test BGE embeddings."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        embedding = model.encode("test")
        print(f"✅ BGE Embeddings: {embedding.shape}")
        return True
    except Exception as e:
        print(f"❌ BGE Embeddings: {e}")
        return False

async def test_whisper():
    """Test faster-whisper."""
    try:
        import faster_whisper
        print(f"✅ Faster-Whisper: Installed")
        return True
    except Exception as e:
        print(f"❌ Faster-Whisper: {e}")
        return False

async def main():
    print("Testing AI Models Setup...")
    print("="*50)
    results = await asyncio.gather(
        test_ollama(),
        test_chroma(),
        test_embeddings(),
        test_whisper()
    )
    print("="*50)
    if all(results):
        print("\n✅ All AI models configured successfully!")
        return 0
    else:
        print("\n❌ Some components failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
