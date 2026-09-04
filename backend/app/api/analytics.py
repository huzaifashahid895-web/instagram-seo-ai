# backend/app/api/analytics.py — Analytics API endpoints
# Cost classification: FREE + OPEN SOURCE

"""
Analytics API endpoints for Instagram performance metrics and insights.

Endpoints:
- GET /analytics/summary - Account performance summary
- GET /analytics/content-types - Performance by content type
- GET /analytics/posting-times - Optimal posting times
- GET /analytics/hashtags - Top performing hashtags
- GET /analytics/growth - Growth metrics and trends
- POST /analytics/sync - Trigger metrics sync from Instagram
"""

from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models import User
from app.services.analytics import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_account_summary(
    social_account_id: uuid.UUID = Query(..., description="Social account ID"),
    start_date: Optional[datetime] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (default: now)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive account performance summary.
    
    Returns:
    - Total engagement (likes, comments, shares, saves)
    - Reach and impressions
    - Average engagement rate
    - Comment sentiment distribution
    - Top performing posts
    """
    # Default to last 30 days if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService()
    summary = await analytics_service.get_account_summary(
        social_account_id=social_account_id,
        start_date=start_date,
        end_date=end_date,
        db=db
    )
    
    return summary


@router.get("/content-types")
async def get_content_type_performance(
    social_account_id: uuid.UUID = Query(..., description="Social account ID"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze performance by content type (image, video, carousel).
    
    Returns average metrics for each content type to help optimize strategy.
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService()
    performance = await analytics_service.get_content_type_performance(
        social_account_id=social_account_id,
        start_date=start_date,
        end_date=end_date,
        db=db
    )
    
    return {
        "content_types": performance,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }


@router.get("/posting-times")
async def get_optimal_posting_times(
    social_account_id: uuid.UUID = Query(..., description="Social account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get optimal posting times based on historical engagement data.
    
    Analyzes all historical posts to find the best hours to post on each day of the week.
    """
    analytics_service = AnalyticsService()
    optimal_times = await analytics_service.get_optimal_posting_times(
        social_account_id=social_account_id,
        db=db
    )
    
    return {
        "optimal_times": optimal_times,
        "note": "Times shown in UTC. Top 3 hours per day based on engagement rate."
    }


@router.get("/hashtags")
async def get_hashtag_performance(
    social_account_id: uuid.UUID = Query(..., description="Social account ID"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(20, ge=1, le=100, description="Number of top hashtags to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top performing hashtags by engagement.
    
    Helps identify which hashtags drive the most engagement.
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService()
    hashtags = await analytics_service.get_hashtag_performance(
        social_account_id=social_account_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
        limit=limit
    )
    
    return {
        "hashtags": hashtags,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }


@router.get("/growth")
async def get_growth_metrics(
    social_account_id: uuid.UUID = Query(..., description="Social account ID"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get account growth metrics and trends.
    
    Returns:
    - Follower growth (absolute and percentage)
    - Engagement trend (increasing/stable/decreasing)
    - Content velocity (posts per week)
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService()
    growth = await analytics_service.get_growth_metrics(
        social_account_id=social_account_id,
        start_date=start_date,
        end_date=end_date,
        db=db
    )
    
    return {
        "growth_metrics": growth,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }


@router.post("/sync/{post_id}")
async def sync_post_metrics(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger metrics sync for a specific post from Instagram API.
    
    Updates ContentPerformance record with latest data.
    """
    analytics_service = AnalyticsService()
    
    try:
        performance = await analytics_service.collect_post_metrics(
            post_id=post_id,
            db=db
        )
        
        return {
            "status": "synced",
            "post_id": str(post_id),
            "performance": {
                "likes": performance.likes_count,
                "comments": performance.comments_count,
                "shares": performance.shares_count,
                "saves": performance.saves_count,
                "reach": performance.reach,
                "impressions": performance.impressions,
                "engagement_rate": round(performance.engagement_rate or 0, 2)
            },
            "synced_at": performance.synced_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync metrics: {str(e)}")


@router.post("/snapshot/{social_account_id}")
async def save_daily_snapshot(
    social_account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save daily analytics snapshot for trend tracking.
    
    Called automatically by scheduled job, but can be triggered manually.
    """
    analytics_service = AnalyticsService()
    
    try:
        snapshot = await analytics_service.save_daily_snapshot(
            social_account_id=social_account_id,
            db=db
        )
        
        return {
            "status": "saved",
            "snapshot_date": snapshot.date.isoformat(),
            "metrics": {
                "followers": snapshot.followers_count,
                "posts": snapshot.posts_count,
                "engagement_rate": round(snapshot.engagement_rate or 0, 2),
                "reach": snapshot.reach,
                "impressions": snapshot.impressions
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save snapshot: {str(e)}")
