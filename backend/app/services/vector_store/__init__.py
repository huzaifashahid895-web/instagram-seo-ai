# backend/app/services/vector_store/__init__.py

from app.services.vector_store.chroma_store import ChromaVectorStore

__all__ = ["ChromaVectorStore"]
