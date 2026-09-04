# backend/app/services/embeddings/sentence_transformers_provider.py — BGE embeddings
# Cost classification: FREE + OPEN SOURCE (MIT)

import logging

from app.services.providers import EmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformersProvider:
    """
    Embedding provider using sentence-transformers with BGE models.
    Model recommendation: 'BAAI/bge-small-en-v1.5' (~130MB, CPU-friendly, strong MTEB score)
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str | None = None) -> None:
        self.model_name = model_name
        self.device = device or "cpu"
        self._model = None

    def _ensure_model(self):
        """Lazy-load the model on first use to avoid slowing down startup."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers not installed. Install with: pip install sentence-transformers"
            ) from exc

        logger.info(f"Loading sentence-transformers model '{self.model_name}' on {self.device}")
        self._model = SentenceTransformer(self.model_name, device=self.device)
        logger.info(f"Model loaded successfully, embedding dimension: {self._model.get_embedding_dimension()}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of text strings.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each a list of floats)
        """
        if not texts:
            return []

        self._ensure_model()
        logger.info(f"Generating embeddings for {len(texts)} texts")

        # sentence-transformers returns numpy arrays, convert to lists
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,  # Normalize for cosine similarity
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        return [embedding.tolist() for embedding in embeddings]

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as a list of floats
        """
        result = self.embed_texts([text])
        return result[0] if result else []

    def get_dimension(self) -> int:
        """Get the embedding dimension of the loaded model."""
        self._ensure_model()
        return self._model.get_sentence_embedding_dimension()


# Default instance using BGE-small-en-v1.5 on CPU
default_embedding_provider = SentenceTransformersProvider(
    model_name="BAAI/bge-small-en-v1.5",
    device="cpu"
)
