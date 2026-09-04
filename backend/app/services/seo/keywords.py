# backend/app/services/seo/keywords.py
# Cost classification: FREE + OPEN SOURCE
"""
Keyword research and matching service for SEO optimization.
Uses semantic similarity and statistical analysis, no paid APIs.
"""

from typing import List, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.providers import LLMProvider, EmbeddingProvider


class KeywordSuggestion(BaseModel):
    """Keyword suggestion with relevance and search volume estimate"""
    keyword: str
    relevance_score: float  # 0-1, semantic similarity to topic
    competition: str  # "low", "medium", "high" (estimated)
    suggested_by: str  # "llm", "semantic", "existing"


class KeywordAnalysis(BaseModel):
    """Analysis of keyword usage in content"""
    target_keywords: List[str]
    found_keywords: List[str]
    missing_keywords: List[str]
    keyword_density: Dict[str, float]  # keyword -> density (%)
    relevance_score: float  # 0-1, overall keyword relevance


class KeywordService:
    """
    Keyword research and matching service.
    
    Design: No paid APIs. Uses:
    - LLM for keyword generation from topic
    - Embeddings for semantic similarity
    - Database for historical keyword performance
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider
    ):
        self.llm = llm_provider
        self.embeddings = embedding_provider
    
    def generate_keywords(
        self,
        topic: str,
        num_keywords: int = 10,
        niche: str | None = None
    ) -> List[KeywordSuggestion]:
        """
        Generate keyword suggestions for a topic using LLM.
        
        Args:
            topic: Topic or content description
            num_keywords: Number of keywords to generate
            niche: Optional niche/industry context
        
        Returns:
            List of keyword suggestions with relevance scores
        """
        prompt = f"""Generate {num_keywords} relevant keywords and phrases for social media content about: {topic}"""
        
        if niche:
            prompt += f"\nNiche/Industry: {niche}"
        
        prompt += """

Requirements:
- Include both broad and long-tail keywords
- Focus on keywords people actually search for
- Mix of informational and commercial intent
- Include variations and related terms

Format as a simple list, one keyword per line."""
        
        system = "You are an SEO and social media keyword research expert."
        
        try:
            response = self.llm.generate(prompt, system=system)
            
            # Parse keywords from response
            lines = response.strip().split('\n')
            keywords = []
            for line in lines:
                # Remove numbering, bullets, extra whitespace
                keyword = line.strip().lstrip('0123456789.-•*) ').strip()
                if keyword:
                    keywords.append(keyword)
            
            # Get embeddings for semantic similarity
            if keywords:
                topic_embedding = self.embeddings.embed_text(topic)
                keyword_embeddings = self.embeddings.embed_texts(keywords)
                
                # Compute relevance scores
                from numpy import dot
                from numpy.linalg import norm
                
                suggestions = []
                for i, keyword in enumerate(keywords[:num_keywords]):
                    similarity = dot(topic_embedding, keyword_embeddings[i]) / (
                        norm(topic_embedding) * norm(keyword_embeddings[i])
                    )
                    
                    # Estimate competition based on keyword length
                    # (longer, more specific keywords = lower competition)
                    words = keyword.split()
                    if len(words) >= 4:
                        competition = "low"
                    elif len(words) >= 2:
                        competition = "medium"
                    else:
                        competition = "high"
                    
                    suggestions.append(KeywordSuggestion(
                        keyword=keyword,
                        relevance_score=round(similarity, 3),
                        competition=competition,
                        suggested_by="llm"
                    ))
                
                # Sort by relevance
                suggestions.sort(key=lambda x: x.relevance_score, reverse=True)
                return suggestions
            
            return []
        
        except Exception as e:
            # Fallback: extract keywords from topic
            words = topic.split()
            return [
                KeywordSuggestion(
                    keyword=topic,
                    relevance_score=1.0,
                    competition="medium",
                    suggested_by="fallback"
                )
            ]
    
    def analyze_keyword_usage(
        self,
        content: str,
        target_keywords: List[str]
    ) -> KeywordAnalysis:
        """
        Analyze keyword usage in content.
        
        Args:
            content: Content text to analyze
            target_keywords: List of target keywords
        
        Returns:
            Keyword analysis with usage metrics
        """
        content_lower = content.lower()
        word_count = len(content.split())
        
        found_keywords = []
        missing_keywords = []
        keyword_density = {}
        
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            count = content_lower.count(keyword_lower)
            
            if count > 0:
                found_keywords.append(keyword)
                density = (count / word_count) * 100 if word_count > 0 else 0
                keyword_density[keyword] = round(density, 2)
            else:
                missing_keywords.append(keyword)
        
        # Compute overall relevance using embeddings
        try:
            content_embedding = self.embeddings.embed_text(content)
            keyword_embeddings = self.embeddings.embed_texts(target_keywords)
            
            from numpy import dot, mean
            from numpy.linalg import norm
            
            similarities = []
            for kw_emb in keyword_embeddings:
                similarity = dot(content_embedding, kw_emb) / (
                    norm(content_embedding) * norm(kw_emb)
                )
                similarities.append(similarity)
            
            relevance_score = float(mean(similarities))
        except Exception:
            # Fallback: percentage of keywords found
            relevance_score = len(found_keywords) / len(target_keywords) if target_keywords else 0.0
        
        return KeywordAnalysis(
            target_keywords=target_keywords,
            found_keywords=found_keywords,
            missing_keywords=missing_keywords,
            keyword_density=keyword_density,
            relevance_score=round(relevance_score, 3)
        )
    
    def suggest_related_keywords(
        self,
        keyword: str,
        num_suggestions: int = 5,
        db: Session | None = None
    ) -> List[KeywordSuggestion]:
        """
        Suggest related keywords using semantic similarity.
        
        Args:
            keyword: Base keyword
            num_suggestions: Number of suggestions
            db: Optional database session for historical data
        
        Returns:
            List of related keyword suggestions
        """
        # If we have DB, fetch existing keywords
        if db:
            from app.models.keyword import Keyword
            
            # Get all keywords from DB
            existing_keywords = db.query(Keyword).all()
            
            if existing_keywords:
                # Compute semantic similarity
                keyword_embedding = self.embeddings.embed_text(keyword)
                keyword_texts = [kw.keyword for kw in existing_keywords]
                keyword_embeddings = self.embeddings.embed_texts(keyword_texts)
                
                from numpy import dot
                from numpy.linalg import norm
                
                suggestions = []
                for i, existing_kw in enumerate(existing_keywords):
                    if existing_kw.keyword.lower() == keyword.lower():
                        continue  # Skip the same keyword
                    
                    similarity = dot(keyword_embedding, keyword_embeddings[i]) / (
                        norm(keyword_embedding) * norm(keyword_embeddings[i])
                    )
                    
                    suggestions.append(KeywordSuggestion(
                        keyword=existing_kw.keyword,
                        relevance_score=round(similarity, 3),
                        competition="medium",  # Could calculate from performance data
                        suggested_by="semantic"
                    ))
                
                # Sort by relevance and return top N
                suggestions.sort(key=lambda x: x.relevance_score, reverse=True)
                return suggestions[:num_suggestions]
        
        # Fallback: Use LLM to generate related keywords
        prompt = f"""List {num_suggestions} keywords and phrases closely related to: {keyword}

Provide synonyms, variations, and semantically similar terms that someone searching for "{keyword}" might also be interested in.

Format as a simple list, one keyword per line."""
        
        system = "You are an SEO keyword research expert."
        
        try:
            response = self.llm.generate(prompt, system=system)
            
            lines = response.strip().split('\n')
            suggestions = []
            for line in lines[:num_suggestions]:
                related = line.strip().lstrip('0123456789.-•*) ').strip()
                if related:
                    suggestions.append(KeywordSuggestion(
                        keyword=related,
                        relevance_score=0.8,  # Default relevance for LLM suggestions
                        competition="medium",
                        suggested_by="llm"
                    ))
            
            return suggestions
        
        except Exception:
            return []
