# backend/tests/content/test_phase2_providers.py — Phase 2 provider integration tests
# Cost classification: FREE + OPEN SOURCE

import pytest
from pathlib import Path

from app.services.providers import TranscriptResult, VisionAnalysis


class TestProviderProtocols:
    """Test that provider implementations conform to their protocols."""

    def test_stt_provider_protocol(self):
        """Test that STT provider implements the required protocol."""
        from app.services.stt.faster_whisper_provider import FasterWhisperProvider
        from app.services.providers import STTProvider

        provider = FasterWhisperProvider(model_size="tiny")  # Use tiny for fast tests
        assert isinstance(provider, STTProvider)
        assert hasattr(provider, "transcribe")

    def test_embedding_provider_protocol(self):
        """Test that embedding provider implements the required protocol."""
        from app.services.embeddings.sentence_transformers_provider import SentenceTransformersProvider
        from app.services.providers import EmbeddingProvider

        provider = SentenceTransformersProvider()
        assert isinstance(provider, EmbeddingProvider)
        assert hasattr(provider, "embed_text")
        assert hasattr(provider, "embed_texts")

    def test_vision_provider_protocol(self):
        """Test that vision provider implements the required protocol."""
        from app.services.vision.clip_vision_provider import CLIPVisionProvider
        from app.services.providers import VisionProvider

        provider = CLIPVisionProvider()
        assert isinstance(provider, VisionProvider)
        assert hasattr(provider, "analyze")
        assert hasattr(provider, "caption")
        assert hasattr(provider, "extract_tags")


class TestEmbeddingProvider:
    """Test embedding provider functionality."""

    def test_embed_text(self):
        """Test single text embedding."""
        from app.services.embeddings.sentence_transformers_provider import default_embedding_provider

        text = "This is a test sentence for embedding generation."
        embedding = default_embedding_provider.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_texts_batch(self):
        """Test batch text embedding."""
        from app.services.embeddings.sentence_transformers_provider import default_embedding_provider

        texts = [
            "First test sentence.",
            "Second test sentence.",
            "Third test sentence.",
        ]
        embeddings = default_embedding_provider.embed_texts(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) > 0 for emb in embeddings)

    def test_embed_empty_list(self):
        """Test embedding empty list returns empty list."""
        from app.services.embeddings.sentence_transformers_provider import default_embedding_provider

        embeddings = default_embedding_provider.embed_texts([])
        assert embeddings == []


class TestVectorStore:
    """Test Chroma vector store functionality."""

    def test_vector_store_initialization(self):
        """Test vector store can be initialized."""
        from app.services.vector_store.chroma_store import ChromaVectorStore

        store = ChromaVectorStore(persist_directory="./test_chroma", collection_name="test_collection")
        assert store is not None

    def test_add_and_search_documents(self):
        """Test adding documents and searching."""
        from app.services.vector_store.chroma_store import ChromaVectorStore
        from app.services.embeddings.sentence_transformers_provider import default_embedding_provider

        store = ChromaVectorStore(persist_directory="./test_chroma", collection_name="test_search")

        # Add test documents with metadata (Chroma requires non-empty metadata)
        texts = ["Machine learning is fascinating", "Python is a programming language"]
        embeddings = default_embedding_provider.embed_texts(texts)
        metadatas = [{"type": "ml"}, {"type": "programming"}]
        ids = store.add_documents(texts=texts, embeddings=embeddings, metadatas=metadatas, ids=["doc1", "doc2"])

        assert len(ids) == 2
        assert "doc1" in ids
        assert "doc2" in ids

        # Search for similar documents
        query_text = "AI and machine learning"
        query_embedding = default_embedding_provider.embed_text(query_text)
        results = store.search(query_embedding, n_results=1)

        assert len(results["ids"]) > 0
        assert "doc1" in results["ids"]  # Should match the ML document


class TestThumbnailGenerator:
    """Test thumbnail generation service."""

    def test_thumbnail_generator_initialization(self):
        """Test thumbnail generator can be initialized."""
        from app.services.thumbnail import ThumbnailGenerator

        generator = ThumbnailGenerator()
        assert generator is not None


def test_all_dependencies_installed():
    """Verify all Phase 2 dependencies are installed."""
    import sys
    
    missing = []
    try:
        import faster_whisper
    except ImportError:
        missing.append("faster-whisper")
    
    try:
        import sentence_transformers
    except ImportError:
        missing.append("sentence-transformers")
    
    try:
        import open_clip
    except ImportError:
        missing.append("open_clip_torch")
    
    try:
        import chromadb
    except ImportError:
        missing.append("chromadb")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")
    
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python-headless")
    
    if missing:
        pytest.fail(
            f"Missing dependencies for Python {sys.version_info.major}.{sys.version_info.minor}: {', '.join(missing)}\n"
            f"Install with: pip install {' '.join(missing)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
