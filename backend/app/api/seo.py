# backend/app/api/seo.py
"""
SEO optimization endpoints.
Provides keyword research, hashtag suggestions, and content scoring.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.seo import (
    SEOScoringService,
    SEOScore,
    KeywordService,
    KeywordSuggestion,
    KeywordAnalysis,
    HashtagService,
    HashtagSuggestion,
    HashtagAnalysis,
    HashtagPerformance,
)
from app.services.llm.ollama_provider import OllamaProvider
from app.services.embeddings.sentence_transformers_provider import SentenceTransformersProvider
from app.services.vector_store.chroma_store import ChromaVectorStore
from pydantic import BaseModel


router = APIRouter()


# Request/Response schemas

class ScoreContentRequest(BaseModel):
    caption: str
    hook: str | None = None
    keywords: List[str] | None = None
    hashtags: List[str] | None = None
    brand_pillars: List[str] | None = None
    target_audience: str | None = None


class GenerateKeywordsRequest(BaseModel):
    topic: str
    niche: str | None = None
    num_keywords: int = 10


class AnalyzeKeywordsRequest(BaseModel):
    content: str
    target_keywords: List[str]


class GenerateHashtagsRequest(BaseModel):
    topic: str
    niche: str | None = None
    num_hashtags: int = 10
    platform: str = "instagram"


class AnalyzeHashtagsRequest(BaseModel):
    hashtags: List[str]
    platform: str = "instagram"


# Dependency injection for services

def get_seo_scoring_service() -> SEOScoringService:
    """Get SEO scoring service with dependencies."""
    llm = OllamaProvider()
    embeddings = SentenceTransformersProvider()
    vector_store = ChromaVectorStore()
    return SEOScoringService(llm, embeddings, vector_store)


def get_keyword_service() -> KeywordService:
    """Get keyword service with dependencies."""
    llm = OllamaProvider()
    embeddings = SentenceTransformersProvider()
    return KeywordService(llm, embeddings)


def get_hashtag_service() -> HashtagService:
    """Get hashtag service with dependencies."""
    llm = OllamaProvider()
    return HashtagService(llm)


# Endpoints

@router.post("/score", response_model=SEOScore)
async def score_content(
    request: ScoreContentRequest,
    current_user: User = Depends(get_current_user),
    seo_service: SEOScoringService = Depends(get_seo_scoring_service)
):
    """
    Compute SEO score for content.
    
    Returns weighted score based on:
    - Topic relevance (embedding similarity to brand pillars)
    - Keyword relevance (keyword matching)
    - Hook strength (LLM-scored)
    - Audience relevance (embedding similarity)
    - Caption quality (deterministic checks)
    - Hashtag quality (historical performance)
    - Content freshness (duplicate detection)
    """
    try:
        score = seo_service.compute_seo_score(
            caption=request.caption,
            hook=request.hook,
            keywords=request.keywords,
            hashtags=request.hashtags,
            brand_pillars=request.brand_pillars,
            target_audience=request.target_audience
        )
        return score
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute SEO score: {str(e)}")


@router.post("/keywords/generate", response_model=List[KeywordSuggestion])
async def generate_keywords(
    request: GenerateKeywordsRequest,
    current_user: User = Depends(get_current_user),
    keyword_service: KeywordService = Depends(get_keyword_service)
):
    """
    Generate keyword suggestions for a topic using LLM + semantic similarity.
    """
    try:
        keywords = keyword_service.generate_keywords(
            topic=request.topic,
            num_keywords=request.num_keywords,
            niche=request.niche
        )
        return keywords
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate keywords: {str(e)}")


@router.post("/keywords/analyze", response_model=KeywordAnalysis)
async def analyze_keywords(
    request: AnalyzeKeywordsRequest,
    current_user: User = Depends(get_current_user),
    keyword_service: KeywordService = Depends(get_keyword_service)
):
    """
    Analyze keyword usage in content.
    """
    try:
        analysis = keyword_service.analyze_keyword_usage(
            content=request.content,
            target_keywords=request.target_keywords
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze keywords: {str(e)}")


@router.get("/keywords/related/{keyword}", response_model=List[KeywordSuggestion])
async def get_related_keywords(
    keyword: str,
    num_suggestions: int = 5,
    current_user: User = Depends(get_current_user),
    keyword_service: KeywordService = Depends(get_keyword_service),
    db: Session = Depends(get_db)
):
    """
    Get related keyword suggestions using semantic similarity.
    """
    try:
        suggestions = keyword_service.suggest_related_keywords(
            keyword=keyword,
            num_suggestions=num_suggestions,
            db=db
        )
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find related keywords: {str(e)}")


@router.post("/hashtags/generate", response_model=List[HashtagSuggestion])
async def generate_hashtags(
    request: GenerateHashtagsRequest,
    current_user: User = Depends(get_current_user),
    hashtag_service: HashtagService = Depends(get_hashtag_service)
):
    """
    Generate hashtag suggestions for content using LLM.
    """
    try:
        hashtags = hashtag_service.generate_hashtags(
            topic=request.topic,
            niche=request.niche,
            num_hashtags=request.num_hashtags,
            platform=request.platform
        )
        return hashtags
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate hashtags: {str(e)}")


@router.post("/hashtags/analyze", response_model=HashtagAnalysis)
async def analyze_hashtags(
    request: AnalyzeHashtagsRequest,
    current_user: User = Depends(get_current_user),
    hashtag_service: HashtagService = Depends(get_hashtag_service)
):
    """
    Analyze hashtag usage quality.
    """
    try:
        analysis = hashtag_service.analyze_hashtag_usage(
            hashtags=request.hashtags,
            platform=request.platform
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze hashtags: {str(e)}")


@router.get("/hashtags/performance/{hashtag}", response_model=HashtagPerformance)
async def get_hashtag_performance(
    hashtag: str,
    days_back: int = 90,
    current_user: User = Depends(get_current_user),
    hashtag_service: HashtagService = Depends(get_hashtag_service),
    db: Session = Depends(get_db)
):
    """
    Get historical performance for a hashtag.
    """
    try:
        performance = hashtag_service.get_hashtag_performance(
            hashtag=hashtag,
            db=db,
            days_back=days_back
        )
        if not performance:
            raise HTTPException(status_code=404, detail="No performance data found for this hashtag")
        return performance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hashtag performance: {str(e)}")


@router.get("/hashtags/top", response_model=List[HashtagPerformance])
async def get_top_hashtags(
    limit: int = 10,
    days_back: int = 30,
    current_user: User = Depends(get_current_user),
    hashtag_service: HashtagService = Depends(get_hashtag_service),
    db: Session = Depends(get_db)
):
    """
    Get top performing hashtags based on historical data.
    """
    try:
        top_hashtags = hashtag_service.get_top_performing_hashtags(
            db=db,
            limit=limit,
            days_back=days_back
        )
        return top_hashtags
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top hashtags: {str(e)}")
