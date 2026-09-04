# backend/app/services/analytics.py — Analytics and metrics collection service
# Cost classification: FREE + OPEN SOURCE

"""
Analytics service for Instagram content performance tracking.

Provides:
1. Performance metrics collection from Instagram API
2. Content analysis and trend detection
3. Engagement rate calculations
4. Audience insights aggregation
5. Dashboard data preparation

Metrics tracked:
- Engagement (likes, comments, shares, saves)
- Reach and impressions
- Follower growth
- Best performing content types
- Optimal posting times
- Hashtag performance
- Comment sentiment distribution
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import (
    Post, ContentPerformance, Comment, SocialAccount,
    ContentAsset, Hashtag, Analytics
)


class AnalyticsService:
    """
    Service for collecting and analyzing Instagram content performance metrics.
    
    Aggregates data from:
    - Instagram Graph API (via scheduled sync)
    - Local database (comments, posts, scheduling)
    - Content analysis results
    """
    
    async def collect_post_metrics(
        self,
        post_id: uuid.UUID,
        db: AsyncSession
    ) -> ContentPerformance:
        """
        Collect performance metrics for a specific post from Instagram API.
        
        Updates ContentPerformance record with latest data.
        """
        post = await db.get(Post, post_id)
        if not post or not post.platform_post_id:
            raise ValueError(f"Post {post_id} not found or not published")
        
        # Get Instagram metrics via Graph API
        # POST https://graph.instagram.com/v18.0/{media-id}/insights
        # metrics: engagement,impressions,reach,saved
        
        # Mock implementation - would call Instagram API here
        metrics = await self._fetch_instagram_metrics(post.platform_post_id)
        
        # Update or create ContentPerformance record
        perf_result = await db.execute(
            select(ContentPerformance).filter_by(post_id=post_id)
        )
        performance = perf_result.scalar_one_or_none()
        
        if not performance:
            performance = ContentPerformance(
                id=uuid.uuid4(),
                post_id=post_id,
                created_at=datetime.utcnow()
            )
            db.add(performance)
        
        # Update metrics
        performance.likes_count = metrics.get("like_count", 0)
        performance.comments_count = metrics.get("comments_count", 0)
        performance.shares_count = metrics.get("shares_count", 0)
        performance.saves_count = metrics.get("saved", 0)
        performance.reach = metrics.get("reach", 0)
        performance.impressions = metrics.get("impressions", 0)
        performance.engagement_rate = self._calculate_engagement_rate(
            likes=performance.likes_count,
            comments=performance.comments_count,
            shares=performance.shares_count,
            saves=performance.saves_count,
            impressions=performance.impressions
        )
        performance.synced_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(performance)
        
        return performance
    
    async def _fetch_instagram_metrics(self, platform_post_id: str) -> Dict[str, int]:
        """Fetch metrics from Instagram Graph API."""
        # Mock implementation
        # In production, would call:
        # GET https://graph.instagram.com/v18.0/{platform_post_id}?fields=like_count,comments_count,insights...
        
        return {
            "like_count": 0,
            "comments_count": 0,
            "shares_count": 0,
            "saved": 0,
            "reach": 0,
            "impressions": 0
        }
    
    def _calculate_engagement_rate(
        self,
        likes: int,
        comments: int,
        shares: int,
        saves: int,
        impressions: int
    ) -> float:
        """Calculate engagement rate as percentage."""
        if impressions == 0:
            return 0.0
        
        total_engagements = likes + comments + shares + saves
        return (total_engagements / impressions) * 100.0
    
    async def get_account_summary(
        self,
        social_account_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get comprehensive account performance summary.
        
        Returns aggregated metrics for date range.
        """
        # Get all posts in date range
        posts_result = await db.execute(
            select(Post)
            .filter(
                and_(
                    Post.social_account_id == social_account_id,
                    Post.published_at >= start_date,
                    Post.published_at <= end_date,
                    Post.status == "published"
                )
            )
        )
        posts = posts_result.scalars().all()
        
        if not posts:
            return self._empty_summary()
        
        # Get performance metrics for all posts
        post_ids = [p.id for p in posts]
        perf_result = await db.execute(
            select(ContentPerformance)
            .filter(ContentPerformance.post_id.in_(post_ids))
        )
        performances = perf_result.scalars().all()
        
        # Aggregate metrics
        total_likes = sum(p.likes_count or 0 for p in performances)
        total_comments = sum(p.comments_count or 0 for p in performances)
        total_shares = sum(p.shares_count or 0 for p in performances)
        total_saves = sum(p.saves_count or 0 for p in performances)
        total_reach = sum(p.reach or 0 for p in performances)
        total_impressions = sum(p.impressions or 0 for p in performances)
        
        avg_engagement_rate = (
            sum(p.engagement_rate or 0 for p in performances) / len(performances)
            if performances else 0.0
        )
        
        # Get comment sentiment distribution
        comments_result = await db.execute(
            select(Comment.sentiment, func.count(Comment.id))
            .join(Post, Comment.post_id == Post.id)
            .filter(
                and_(
                    Post.social_account_id == social_account_id,
                    Comment.created_at >= start_date,
                    Comment.created_at <= end_date
                )
            )
            .group_by(Comment.sentiment)
        )
        sentiment_counts = dict(comments_result.all())
        
        # Get top performing posts
        top_posts_result = await db.execute(
            select(Post, ContentPerformance)
            .join(ContentPerformance, Post.id == ContentPerformance.post_id)
            .filter(Post.id.in_(post_ids))
            .order_by(desc(ContentPerformance.engagement_rate))
            .limit(5)
        )
        top_posts = [
            {
                "post_id": str(post.id),
                "caption": post.caption[:100] if post.caption else "",
                "post_type": post.post_type,
                "engagement_rate": perf.engagement_rate,
                "likes": perf.likes_count,
                "published_at": post.published_at.isoformat() if post.published_at else None
            }
            for post, perf in top_posts_result.all()
        ]
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "posts_count": len(posts),
            "total_engagement": {
                "likes": total_likes,
                "comments": total_comments,
                "shares": total_shares,
                "saves": total_saves
            },
            "reach": {
                "total": total_reach,
                "impressions": total_impressions
            },
            "engagement_rate": {
                "average": round(avg_engagement_rate, 2),
                "total_engagements": total_likes + total_comments + total_shares + total_saves
            },
            "comment_sentiment": {
                "positive": sentiment_counts.get("positive", 0),
                "neutral": sentiment_counts.get("neutral", 0),
                "negative": sentiment_counts.get("negative", 0)
            },
            "top_posts": top_posts
        }
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary structure."""
        return {
            "date_range": {},
            "posts_count": 0,
            "total_engagement": {"likes": 0, "comments": 0, "shares": 0, "saves": 0},
            "reach": {"total": 0, "impressions": 0},
            "engagement_rate": {"average": 0.0, "total_engagements": 0},
            "comment_sentiment": {"positive": 0, "neutral": 0, "negative": 0},
            "top_posts": []
        }
    
    async def get_content_type_performance(
        self,
        social_account_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Dict[str, float]]:
        """
        Analyze performance by content type (image, video, carousel).
        
        Returns average metrics for each type.
        """
        result = await db.execute(
            select(
                Post.post_type,
                func.avg(ContentPerformance.engagement_rate).label("avg_engagement"),
                func.avg(ContentPerformance.likes_count).label("avg_likes"),
                func.avg(ContentPerformance.comments_count).label("avg_comments"),
                func.count(Post.id).label("count")
            )
            .join(ContentPerformance, Post.id == ContentPerformance.post_id)
            .filter(
                and_(
                    Post.social_account_id == social_account_id,
                    Post.published_at >= start_date,
                    Post.published_at <= end_date,
                    Post.status == "published"
                )
            )
            .group_by(Post.post_type)
        )
        
        performance_by_type = {}
        for row in result.all():
            performance_by_type[row.post_type] = {
                "avg_engagement_rate": round(row.avg_engagement or 0, 2),
                "avg_likes": round(row.avg_likes or 0, 1),
                "avg_comments": round(row.avg_comments or 0, 1),
                "count": row.count
            }
        
        return performance_by_type
    
    async def get_optimal_posting_times(
        self,
        social_account_id: uuid.UUID,
        db: AsyncSession
    ) -> Dict[str, List[int]]:
        """
        Analyze historical data to find optimal posting times.
        
        Returns best hours for each day of the week.
        """
        # Get all published posts with performance data
        result = await db.execute(
            select(Post, ContentPerformance)
            .join(ContentPerformance, Post.id == ContentPerformance.post_id)
            .filter(
                and_(
                    Post.social_account_id == social_account_id,
                    Post.status == "published",
                    Post.published_at.isnot(None)
                )
            )
        )
        
        posts_performance = result.all()
        
        # Group by day of week and hour
        day_hour_engagement = {}
        for post, perf in posts_performance:
            if not post.published_at:
                continue
            
            day_of_week = post.published_at.strftime("%A")  # Monday, Tuesday, etc.
            hour = post.published_at.hour
            
            key = f"{day_of_week}_{hour}"
            if key not in day_hour_engagement:
                day_hour_engagement[key] = []
            
            day_hour_engagement[key].append(perf.engagement_rate or 0)
        
        # Calculate average engagement for each day-hour combination
        avg_engagement = {}
        for key, rates in day_hour_engagement.items():
            avg_engagement[key] = sum(rates) / len(rates)
        
        # Find top 3 hours for each day
        optimal_times = {}
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            day_hours = {
                hour: avg_engagement.get(f"{day}_{hour}", 0)
                for hour in range(24)
            }
            
            # Sort by engagement and get top 3
            top_hours = sorted(day_hours.items(), key=lambda x: x[1], reverse=True)[:3]
            optimal_times[day] = [hour for hour, _ in top_hours]
        
        return optimal_times
    
    async def get_hashtag_performance(
        self,
        social_account_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Analyze hashtag performance across posts.
        
        Returns top performing hashtags by engagement.
        """
        # Get all posts in date range
        posts_result = await db.execute(
            select(Post.id)
            .filter(
                and_(
                    Post.social_account_id == social_account_id,
                    Post.published_at >= start_date,
                    Post.published_at <= end_date,
                    Post.status == "published"
                )
            )
        )
        post_ids = [row[0] for row in posts_result.all()]
        
        if not post_ids:
            return []
        
        # Get hashtags used in these posts
        hashtag_result = await db.execute(
            select(
                Hashtag.tag,
                func.count(Hashtag.id).label("usage_count"),
                func.avg(ContentPerformance.engagement_rate).label("avg_engagement")
            )
            .join(Post, Hashtag.post_id == Post.id)
            .join(ContentPerformance, Post.id == ContentPerformance.post_id)
            .filter(Hashtag.post_id.in_(post_ids))
            .group_by(Hashtag.tag)
            .order_by(desc("avg_engagement"))
            .limit(limit)
        )
        
        return [
            {
                "hashtag": row.tag,
                "usage_count": row.usage_count,
                "avg_engagement_rate": round(row.avg_engagement or 0, 2)
            }
            for row in hashtag_result.all()
        ]
    
    async def get_growth_metrics(
        self,
        social_account_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Track account growth over time.
        
        Returns follower growth, engagement trends, content velocity.
        """
        # Get analytics snapshots
        analytics_result = await db.execute(
            select(Analytics)
            .filter(
                and_(
                    Analytics.social_account_id == social_account_id,
                    Analytics.date >= start_date.date(),
                    Analytics.date <= end_date.date()
                )
            )
            .order_by(Analytics.date)
        )
        snapshots = analytics_result.scalars().all()
        
        if not snapshots:
            return {
                "follower_growth": 0,
                "engagement_trend": "stable",
                "avg_posts_per_week": 0
            }
        
        # Calculate follower growth
        first_snapshot = snapshots[0]
        last_snapshot = snapshots[-1]
        follower_growth = (
            last_snapshot.followers_count - first_snapshot.followers_count
            if first_snapshot.followers_count > 0 else 0
        )
        growth_percentage = (
            (follower_growth / first_snapshot.followers_count) * 100
            if first_snapshot.followers_count > 0 else 0
        )
        
        # Analyze engagement trend
        engagement_rates = [s.engagement_rate for s in snapshots if s.engagement_rate]
        engagement_trend = "stable"
        if len(engagement_rates) >= 2:
            if engagement_rates[-1] > engagement_rates[0] * 1.1:
                engagement_trend = "increasing"
            elif engagement_rates[-1] < engagement_rates[0] * 0.9:
                engagement_trend = "decreasing"
        
        # Calculate content velocity
        posts_result = await db.execute(
            select(func.count(Post.id))
            .filter(
                and_(
                    Post.social_account_id == social_account_id,
                    Post.published_at >= start_date,
                    Post.published_at <= end_date,
                    Post.status == "published"
                )
            )
        )
        total_posts = posts_result.scalar() or 0
        days_diff = (end_date - start_date).days or 1
        avg_posts_per_week = (total_posts / days_diff) * 7
        
        return {
            "follower_growth": follower_growth,
            "growth_percentage": round(growth_percentage, 2),
            "engagement_trend": engagement_trend,
            "avg_posts_per_week": round(avg_posts_per_week, 1),
            "total_posts": total_posts
        }
    
    async def save_daily_snapshot(
        self,
        social_account_id: uuid.UUID,
        db: AsyncSession
    ) -> Analytics:
        """
        Save daily analytics snapshot for tracking trends over time.
        
        Called by scheduled job daily.
        """
        today = datetime.utcnow().date()
        
        # Check if snapshot already exists for today
        existing_result = await db.execute(
            select(Analytics)
            .filter(
                and_(
                    Analytics.social_account_id == social_account_id,
                    Analytics.date == today
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            return existing  # Already captured today
        
        # Get account summary for today
        summary = await self.get_account_summary(
            social_account_id=social_account_id,
            start_date=datetime.combine(today, datetime.min.time()),
            end_date=datetime.combine(today, datetime.max.time()),
            db=db
        )
        
        # Get account from Instagram API for follower count
        # In production: GET https://graph.instagram.com/v18.0/{ig-user-id}?fields=followers_count,follows_count
        account = await db.get(SocialAccount, social_account_id)
        
        # Create snapshot
        snapshot = Analytics(
            id=uuid.uuid4(),
            social_account_id=social_account_id,
            date=today,
            followers_count=0,  # Would fetch from Instagram API
            following_count=0,  # Would fetch from Instagram API
            posts_count=summary["posts_count"],
            engagement_rate=summary["engagement_rate"]["average"],
            reach=summary["reach"]["total"],
            impressions=summary["reach"]["impressions"],
            created_at=datetime.utcnow()
        )
        
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        
        return snapshot
