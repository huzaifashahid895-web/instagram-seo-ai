# backend/app/services/vector_store/chroma_store.py — Chroma vector database integration
# Cost classification: FREE + OPEN SOURCE (Apache 2.0), LOCAL ONLY

import logging
import uuid
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """
    Vector store using Chroma for RAG and semantic search.
    Runs in embedded mode (in-process) or as a local server.
    """

    def __init__(
        self,
        persist_directory: str | Path | None = None,
        collection_name: str = "content_embeddings",
    ) -> None:
        self.persist_directory = Path(persist_directory or settings.CHROMA_PERSIST_DIR).resolve()
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _ensure_client(self):
        """Lazy-load the Chroma client on first use."""
        if self._client is not None:
            return

        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "chromadb not installed. Install with: pip install chromadb"
            ) from exc

        logger.info(f"Initializing Chroma client with persist_directory={self.persist_directory}")
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self._client = chromadb.PersistentClient(path=str(self.persist_directory))
        logger.info("Chroma client initialized successfully")

    def _get_collection(self):
        """Get or create the collection."""
        self._ensure_client()
        
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"Using collection '{self.collection_name}'")
        
        return self._collection

    def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        """
        Add documents with embeddings to the vector store.

        Args:
            texts: List of text content
            embeddings: List of embedding vectors
            metadatas: Optional list of metadata dicts
            ids: Optional list of document IDs (generated if not provided)

        Returns:
            List of document IDs
        """
        collection = self._get_collection()

        if not texts or not embeddings:
            return []

        if len(texts) != len(embeddings):
            raise ValueError("texts and embeddings must have the same length")

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]

        # Ensure metadatas has the right length
        if metadatas is None:
            metadatas = [{} for _ in texts]
        elif len(metadatas) != len(texts):
            raise ValueError("metadatas must have the same length as texts")

        logger.info(f"Adding {len(texts)} documents to collection '{self.collection_name}'")
        
        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        return ids

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Search for similar documents using a query embedding.

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter (Chroma where clause)

        Returns:
            Dict with 'ids', 'documents', 'metadatas', 'distances'
        """
        collection = self._get_collection()

        logger.info(f"Searching collection '{self.collection_name}' for {n_results} results")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

        # Flatten single-query results
        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
        }

    def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        """
        Retrieve a document by its ID.

        Args:
            document_id: Document ID

        Returns:
            Dict with 'id', 'document', 'metadata', 'embedding' or None if not found
        """
        collection = self._get_collection()

        try:
            result = collection.get(ids=[document_id], include=["documents", "metadatas", "embeddings"])
            
            if not result["ids"]:
                return None

            return {
                "id": result["ids"][0],
                "document": result["documents"][0] if result["documents"] else None,
                "metadata": result["metadatas"][0] if result["metadatas"] else {},
                "embedding": result["embeddings"][0] if result["embeddings"] else None,
            }
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None

    def delete_by_id(self, document_id: str) -> bool:
        """
        Delete a document by its ID.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        collection = self._get_collection()

        try:
            collection.delete(ids=[document_id])
            logger.info(f"Deleted document {document_id} from collection '{self.collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    def delete_by_metadata(self, where: dict[str, Any]) -> int:
        """
        Delete documents matching metadata filter.

        Args:
            where: Metadata filter (Chroma where clause)

        Returns:
            Number of documents deleted
        """
        collection = self._get_collection()

        try:
            collection.delete(where=where)
            logger.info(f"Deleted documents from collection '{self.collection_name}' with filter {where}")
            # Note: Chroma doesn't return count, so we can't know exactly how many were deleted
            return -1
        except Exception as e:
            logger.error(f"Error deleting documents with filter {where}: {e}")
            return 0

    def count(self) -> int:
        """Get the total number of documents in the collection."""
        collection = self._get_collection()
        return collection.count()


# Default instance for content embeddings
default_vector_store = ChromaVectorStore(
    persist_directory=settings.CHROMA_PERSIST_DIR if hasattr(settings, "CHROMA_PERSIST_DIR") else "./chroma_data",
    collection_name="content_embeddings"
)
