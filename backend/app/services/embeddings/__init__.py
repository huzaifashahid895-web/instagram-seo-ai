# backend/app/services/embeddings/__init__.py

from app.services.embeddings.sentence_transformers_provider import SentenceTransformersProvider

__all__ = ["SentenceTransformersProvider"]
