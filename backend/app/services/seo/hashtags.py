# backend/app/services/seo/hashtags.py
# Cost classification: FREE + OPEN SOURCE
"""
Hashtag research and performance tracking service.
Uses LLM generation + historical performance data, no paid APIs.
"""

from typing import List, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.providers import LLMProvider


class HashtagSuggestion(BaseModel):
    """Hashtag suggestion with metadata"""
    hashtag: str  # Without # prefix
    category: str  # "trending", "niche", "branded", "community"
    estimated_reach: str  # "small", "medium", "large"
    relevance_score: float  # 0-1
    suggested_by: str  # "llm", "performance", "trending"


class HashtagPerformance(BaseModel):
    """Historical performance metrics for a hashtag"""
    hashtag: str
    usage_count: int
    avg_likes: float
    avg_comments: float
    avg_engagement_rate: float
    last_used: datetime | None


class HashtagAnalysis(BaseModel):
    """Analysis of hashtag usage"""
    total_hashtags: int
    recommended_count: int  # 3-5 for Instagram
    categories: Dict[str, int]  # category -> count
    quality_score: float  # 0-1
    suggestions: List[str]  # Improvement suggestions


class HashtagService:
    """
    Hashtag research and performance tracking service.
    
    Design: No paid APIs. Uses:
    - LLM for hashtag generation
    - Database for historical performance tracking
    - Simple heuristics for categorization
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        
        # Optimal hashtag count per platform
        self.optimal_count = {
            "instagram": (3, 5),  # Min, max recommended
            "twitter": (1, 2),
            "linkedin": (3, 5)
        }
    
    def generate_hashtags(
        self,
        topic: str,
        niche: str | None = None,
        num_hashtags: int = 10,
        platform: str = "instagram"
    ) -> List[HashtagSuggestion]:
        """
        Generate hashtag suggestions using LLM.
        
        Args:
            topic: Content topic or description
            niche: Optional niche/industry
            num_hashtags: Number of hashtags to generate
            platform: Target platform (instagram, twitter, linkedin)
        
        Returns:
            List of hashtag suggestions
        """
        prompt = f"""Generate {num_hashtags} effective hashtags for {platform} content about: {topic}"""
        
        if niche:
            prompt += f"\nNiche: {niche}"
        
        prompt += f"""

Mix of:
- 2-3 broad/popular hashtags (higher reach, more competition)
- 4-5 niche-specific hashtags (targeted audience)
- 2-3 long-tail/specific hashtags (lower competition)

Guidelines:
- Relevant to the content topic
- Mix of popular and niche
- No banned or spammy hashtags
- Use actual hashtags people search for

Format: List hashtags WITHOUT the # symbol, one per line."""
        
        system = "You are a social media growth expert specializing in hashtag research."
        
        try:
            response = self.llm.generate(prompt, system=system)
            
            # Parse hashtags from response
            lines = response.strip().split('\n')
            suggestions = []
            
            for line in lines:
                # Remove # if present, numbering, bullets
                hashtag = line.strip().lstrip('#0123456789.-•*) ').strip()
                hashtag = hashtag.replace('#', '').replace(' ', '')  # Remove # and spaces
                
                if hashtag:
                    # Categorize based on length and word count
                    words = len(hashtag.split())
                    length = len(hashtag)
                    
                    if length < 10:
                        category = "trending"
                        reach = "large"
                        relevance = 0.7
                    elif length < 20:
                        category = "niche"
                        reach = "medium"
                        relevance = 0.9
                    else:
                        category = "community"
                        reach = "small"
                        relevance = 0.95
                    
                    suggestions.append(HashtagSuggestion(
                        hashtag=hashtag,
                        category=category,
                        estimated_reach=reach,
                        relevance_score=relevance,
                        suggested_by="llm"
                    ))
            
            return suggestions[:num_hashtags]
        
        except Exception as e:
            # Fallback: extract simple hashtags from topic
            words = topic.lower().split()
            fallback = [
                HashtagSuggestion(
                    hashtag="".join(word.capitalize() for word in words[:3]),
                    category="niche",
                    estimated_reach="medium",
                    relevance_score=1.0,
                    suggested_by="fallback"
                )
            ]
            return fallback
    
    def get_hashtag_performance(
        self,
        hashtag: str,
        db: Session,
        days_back: int = 90
    ) -> HashtagPerformance | None:
        """
        Get historical performance for a hashtag.
        
        Args:
            hashtag: Hashtag to analyze (without #)
            db: Database session
            days_back: Number of days to look back
        
        Returns:
            Performance metrics or None if no data
        """
        from app.models.hashtag import Hashtag
        from app.models.content_performance import ContentPerformance
        
        # Find hashtag in database
        hashtag_clean = hashtag.lstrip('#')
        db_hashtag = db.query(Hashtag).filter(
            func.lower(Hashtag.tag) == hashtag_clean.lower()
        ).first()
        
        if not db_hashtag:
            return None
        
        # Get performance data for posts using this hashtag
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Query content_performance for posts with this hashtag
        # Note: This requires a many-to-many relationship via post_hashtags
        # For now, return basic usage stats
        
        return HashtagPerformance(
            hashtag=hashtag_clean,
            usage_count=db_hashtag.frequency or 0,
            avg_likes=0.0,  # TODO: Calculate from content_performance
            avg_comments=0.0,  # TODO: Calculate from content_performance
            avg_engagement_rate=0.0,  # TODO: Calculate from content_performance
            last_used=db_hashtag.last_used_at
        )
    
    def analyze_hashtag_usage(
        self,
        hashtags: List[str],
        platform: str = "instagram"
    ) -> HashtagAnalysis:
        """
        Analyze hashtag usage quality.
        
        Args:
            hashtags: List of hashtags (with or without #)
            platform: Target platform
        
        Returns:
            Hashtag usage analysis with recommendations
        """
        # Clean hashtags
        clean_hashtags = [h.lstrip('#') for h in hashtags]
        total = len(clean_hashtags)
        
        # Get optimal count for platform
        min_rec, max_rec = self.optimal_count.get(platform, (3, 5))
        
        # Categorize hashtags by length
        categories = {
            "trending": 0,  # Short, broad
            "niche": 0,     # Medium, specific
            "community": 0, # Long, very specific
        }
        
        for tag in clean_hashtags:
            length = len(tag)
            if length < 10:
                categories["trending"] += 1
            elif length < 20:
                categories["niche"] += 1
            else:
                categories["community"] += 1
        
        # Compute quality score
        quality_score = 0.0
        suggestions = []
        
        # Check count
        if total < min_rec:
            quality_score -= 0.3
            suggestions.append(f"Add {min_rec - total} more hashtags (recommended {min_rec}-{max_rec})")
        elif total > max_rec:
            quality_score -= 0.2
            suggestions.append(f"Consider reducing to {max_rec} hashtags for better engagement")
        else:
            quality_score += 0.4
        
        # Check balance
        has_trending = categories["trending"] > 0
        has_niche = categories["niche"] > 0
        
        if has_trending and has_niche:
            quality_score += 0.3
        else:
            if not has_trending:
                suggestions.append("Add 1-2 popular hashtags for broader reach")
            if not has_niche:
                suggestions.append("Add niche-specific hashtags for targeted audience")
            quality_score -= 0.2
        
        # Penalize if too many trending (competition)
        if categories["trending"] > 3:
            quality_score -= 0.1
            suggestions.append("Too many popular hashtags may increase competition")
        
        # Bonus for good mix
        if 1 <= categories["trending"] <= 3 and categories["niche"] >= 3:
            quality_score += 0.3
        
        # Normalize to 0-1
        quality_score = max(0.0, min(1.0, quality_score + 0.5))
        
        if not suggestions:
            suggestions.append("Hashtag strategy looks good!")
        
        return HashtagAnalysis(
            total_hashtags=total,
            recommended_count=max_rec,
            categories=categories,
            quality_score=round(quality_score, 3),
            suggestions=suggestions
        )
    
    def track_hashtag_performance(
        self,
        hashtag: str,
        post_id: str,
        likes: int,
        comments: int,
        db: Session
    ):
        """
        Track hashtag performance for a post.
        
        Args:
            hashtag: Hashtag used (without #)
            post_id: ID of the post
            likes: Number of likes
            comments: Number of comments
            db: Database session
        """
        from app.models.hashtag import Hashtag
        
        hashtag_clean = hashtag.lstrip('#')
        
        # Find or create hashtag
        db_hashtag = db.query(Hashtag).filter(
            func.lower(Hashtag.tag) == hashtag_clean.lower()
        ).first()
        
        if not db_hashtag:
            db_hashtag = Hashtag(
                tag=hashtag_clean,
                frequency=0,
                last_used_at=datetime.utcnow()
            )
            db.add(db_hashtag)
        
        # Update frequency and last used
        db_hashtag.frequency = (db_hashtag.frequency or 0) + 1
        db_hashtag.last_used_at = datetime.utcnow()
        
        db.commit()
    
    def get_top_performing_hashtags(
        self,
        db: Session,
        limit: int = 10,
        days_back: int = 30
    ) -> List[HashtagPerformance]:
        """
        Get top performing hashtags based on historical data.
        
        Args:
            db: Database session
            limit: Number of hashtags to return
            days_back: Number of days to analyze
        
        Returns:
            List of top performing hashtags
        """
        from app.models.hashtag import Hashtag
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Query hashtags used recently, ordered by frequency
        top_hashtags = db.query(Hashtag).filter(
            Hashtag.last_used_at >= cutoff_date
        ).order_by(
            Hashtag.frequency.desc()
        ).limit(limit).all()
        
        results = []
        for tag in top_hashtags:
            results.append(HashtagPerformance(
                hashtag=tag.tag,
                usage_count=tag.frequency or 0,
                avg_likes=0.0,  # TODO: Calculate from content_performance
                avg_comments=0.0,  # TODO: Calculate from content_performance
                avg_engagement_rate=0.0,  # TODO: Calculate from content_performance
                last_used=tag.last_used_at
            ))
        
        return results
