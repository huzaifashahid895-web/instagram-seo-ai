# backend/app/services/rag.py
# Cost classification: FREE + OPEN SOURCE
"""
RAG (Retrieval Augmented Generation) service.
Combines semantic search with LLM generation for context-aware responses.
"""

from typing import List
from pydantic import BaseModel

from app.services.providers import LLMProvider, EmbeddingProvider
from app.services.vector_store.chroma_store import ChromaVectorStore


class RAGContext(BaseModel):
    """Context retrieved from vector store"""
    content: str
    metadata: dict
    score: float


class RAGService:
    """RAG service for semantic search + LLM generation"""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: ChromaVectorStore
    ):
        self.llm = llm_provider
        self.embeddings = embedding_provider
        self.vector_store = vector_store
    
    def retrieve(
        self,
        query: str,
        collection: str = "content",
        top_k: int = 5,
        filters: dict | None = None
    ) -> List[RAGContext]:
        """
        Retrieve relevant context from vector store.
        
        Args:
            query: Search query
            collection: Vector store collection name (ignored, collection set at init)
            top_k: Number of results to retrieve
            filters: Optional metadata filters
        
        Returns:
            List of relevant contexts with scores
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_text(query)
        
        # Search vector store (ChromaVectorStore uses collection from __init__)
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=top_k,
            where=filters
        )
        
        # Convert to RAGContext objects
        # ChromaVectorStore returns: {ids, documents, metadatas, distances}
        contexts = []
        for i in range(len(results.get("ids", []))):
            contexts.append(RAGContext(
                content=results["documents"][i],
                metadata=results["metadatas"][i],
                score=1.0 - results["distances"][i]  # Convert distance to similarity score
            ))
        
        return contexts
    
    def generate_with_context(
        self,
        query: str,
        system: str | None = None,
        collection: str = "content",
        top_k: int = 5,
        filters: dict | None = None,
        **llm_kwargs
    ) -> str:
        """
        Generate response using retrieved context.
        
        Args:
            query: User query
            system: Optional system message
            collection: Vector store collection
            top_k: Number of contexts to retrieve
            filters: Optional metadata filters
            **llm_kwargs: Additional LLM parameters
        
        Returns:
            Generated response
        """
        # Retrieve relevant contexts
        contexts = self.retrieve(query, collection, top_k, filters)
        
        if not contexts:
            # No context found, generate without RAG
            return self.llm.generate(query, system=system, **llm_kwargs)
        
        # Build context-aware prompt
        context_text = "\n\n".join([
            f"[Context {i+1} (relevance: {ctx.score:.2f})]:\n{ctx.content}"
            for i, ctx in enumerate(contexts)
        ])
        
        enhanced_prompt = f"""Based on the following context, answer the user's query.

{context_text}

User query: {query}

Provide a helpful and accurate response based on the context above."""
        
        # Generate response
        return self.llm.generate(enhanced_prompt, system=system, **llm_kwargs)
    
    def generate_ideas_from_content(
        self,
        topic: str,
        brand_profile_id: str | None = None,
        num_ideas: int = 5,
        **llm_kwargs
    ) -> List[str]:
        """
        Generate content ideas based on existing content library.
        
        Args:
            topic: Content topic or theme
            brand_profile_id: Optional brand profile filter
            num_ideas: Number of ideas to generate
            **llm_kwargs: Additional LLM parameters
        
        Returns:
            List of content ideas
        """
        # Build filters
        filters = {}
        if brand_profile_id:
            filters["brand_profile_id"] = brand_profile_id
        
        # Retrieve relevant content
        contexts = self.retrieve(
            query=topic,
            collection="content",
            top_k=10,
            filters=filters if filters else None
        )
        
        # Build prompt
        if contexts:
            context_summaries = "\n".join([
                f"- {ctx.metadata.get('type', 'content')}: {ctx.content[:200]}..."
                for ctx in contexts[:5]
            ])
            
            prompt = f"""Given the following existing content:

{context_summaries}

Generate {num_ideas} fresh, creative content ideas related to: {topic}

Each idea should:
- Be unique and different from existing content
- Be engaging and shareable
- Be specific and actionable
- Include a brief description (1-2 sentences)

Format as a numbered list."""
        else:
            prompt = f"""Generate {num_ideas} fresh, creative content ideas related to: {topic}

Each idea should:
- Be engaging and shareable
- Be specific and actionable
- Include a brief description (1-2 sentences)

Format as a numbered list."""
        
        system = "You are a creative content strategist for social media."
        
        response = self.llm.generate(prompt, system=system, **llm_kwargs)
        
        # Parse ideas from response
        ideas = []
        for line in response.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                # Remove numbering/bullets
                idea = line.lstrip("0123456789.-•) ").strip()
                if idea:
                    ideas.append(idea)
        
        return ideas[:num_ideas]
    
    def generate_caption(
        self,
        content_description: str,
        style: str = "engaging",
        max_length: int = 2200,
        include_hashtags: bool = True,
        brand_voice: str | None = None,
        **llm_kwargs
    ) -> str:
        """
        Generate caption for social media post.
        
        Args:
            content_description: Description of the content
            style: Caption style (engaging, professional, casual, etc.)
            max_length: Maximum caption length
            include_hashtags: Whether to include hashtags
            brand_voice: Optional brand voice description
            **llm_kwargs: Additional LLM parameters
        
        Returns:
            Generated caption
        """
        # Retrieve similar content for style reference
        contexts = self.retrieve(
            query=content_description,
            collection="content",
            top_k=3
        )
        
        # Build prompt
        prompt_parts = [f"Write a {style} social media caption for the following content:"]
        prompt_parts.append(f"\n{content_description}")
        
        if brand_voice:
            prompt_parts.append(f"\nBrand voice: {brand_voice}")
        
        if contexts:
            prompt_parts.append("\nReference style from similar content:")
            for ctx in contexts[:2]:
                if "caption" in ctx.metadata:
                    prompt_parts.append(f"- {ctx.metadata['caption'][:150]}...")
        
        prompt_parts.append(f"\nRequirements:")
        prompt_parts.append(f"- Maximum {max_length} characters")
        prompt_parts.append(f"- {style.capitalize()} tone")
        if include_hashtags:
            prompt_parts.append("- Include 3-5 relevant hashtags at the end")
        prompt_parts.append("- Hook the audience in the first line")
        prompt_parts.append("- Include a call-to-action")
        
        prompt = "\n".join(prompt_parts)
        
        system = "You are an expert social media copywriter."
        
        return self.llm.generate(prompt, system=system, **llm_kwargs)
