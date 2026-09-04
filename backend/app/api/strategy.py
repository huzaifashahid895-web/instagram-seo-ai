# backend/app/api/strategy.py — Content strategy CRUD endpoints
# Cost classification: FREE + OPEN SOURCE

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.content_strategy import ContentStrategy
from app.models.brand_profile import BrandProfile

router = APIRouter()


@router.get("/strategies")
async def list_strategies(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all content strategies for the current user."""
    # ContentStrategy links to BrandProfile, which links to User
    strategies = db.query(ContentStrategy).join(
        BrandProfile, ContentStrategy.brand_profile_id == BrandProfile.id
    ).filter(
        BrandProfile.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return {
        "strategies": [
            {
                "id": str(s.id),
                "brand_profile_id": str(s.brand_profile_id),
                "name": s.name,
                "niche_focus": s.niche_focus,
                "target_audience": s.target_audience,
                "content_pillars": s.content_pillars,
                "posting_plan": s.posting_plan,
                "seo_focus_keywords": s.seo_focus_keywords,
                "avoid_topics": s.avoid_topics,
                "rationale": s.rationale,
                "predicted_score": s.predicted_score,
                "status": s.status.value if s.status else None,
                "is_active": s.is_active,
                "effective_from": s.effective_from.isoformat() if s.effective_from else None,
                "effective_until": s.effective_until.isoformat() if s.effective_until else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in strategies
        ],
        "total": db.query(ContentStrategy).join(
            BrandProfile, ContentStrategy.brand_profile_id == BrandProfile.id
        ).filter(BrandProfile.user_id == current_user.id).count()
    }


@router.post("/strategies")
async def create_strategy(
    name: str,
    description: str = None,
    target_audience: dict = None,
    content_pillars: List[str] = None,
    posting_frequency: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new content strategy."""
    strategy = ContentStrategy(
        user_id=current_user.id,
        name=name,
        description=description,
        target_audience=target_audience,
        content_pillars=content_pillars,
        posting_frequency=posting_frequency,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific strategy by ID."""
    strategy = db.query(ContentStrategy).filter(
        ContentStrategy.id == strategy_id,
        ContentStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "target_audience": strategy.target_audience,
        "content_pillars": strategy.content_pillars,
        "posting_frequency": strategy.posting_frequency,
        "best_times": strategy.best_times,
        "hashtag_strategy": strategy.hashtag_strategy,
        "engagement_tactics": strategy.engagement_tactics,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
        "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
    }


@router.put("/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    name: str = None,
    description: str = None,
    target_audience: dict = None,
    content_pillars: List[str] = None,
    posting_frequency: str = None,
    best_times: List[str] = None,
    hashtag_strategy: dict = None,
    engagement_tactics: List[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing strategy."""
    strategy = db.query(ContentStrategy).filter(
        ContentStrategy.id == strategy_id,
        ContentStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if name is not None:
        strategy.name = name
    if description is not None:
        strategy.description = description
    if target_audience is not None:
        strategy.target_audience = target_audience
    if content_pillars is not None:
        strategy.content_pillars = content_pillars
    if posting_frequency is not None:
        strategy.posting_frequency = posting_frequency
    if best_times is not None:
        strategy.best_times = best_times
    if hashtag_strategy is not None:
        strategy.hashtag_strategy = hashtag_strategy
    if engagement_tactics is not None:
        strategy.engagement_tactics = engagement_tactics
    
    db.commit()
    db.refresh(strategy)
    
    return {
        "id": strategy.id,
        "name": strategy.name,
        "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
    }


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a strategy."""
    strategy = db.query(ContentStrategy).filter(
        ContentStrategy.id == strategy_id,
        ContentStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    db.delete(strategy)
    db.commit()
    
    return {"message": "Strategy deleted successfully"}
