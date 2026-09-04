# backend/app/api/approvals.py — Content approval queue management
# Cost classification: FREE + OPEN SOURCE

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.approval_queue import ApprovalQueue

router = APIRouter()


@router.get("")
async def list_approvals(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all items in approval queue for the current user."""
    query = db.query(ApprovalQueue).filter(ApprovalQueue.requested_by_user_id == current_user.id)
    
    if status:
        query = query.filter(ApprovalQueue.status == status)
    
    approvals = query.offset(skip).limit(limit).all()
    
    return {
        "approvals": [
            {
                "id": str(approval.id),
                "requested_by_user_id": str(approval.requested_by_user_id) if approval.requested_by_user_id else None,
                "reviewed_by_user_id": str(approval.reviewed_by_user_id) if approval.reviewed_by_user_id else None,
                "entity_type": approval.entity_type,
                "entity_id": str(approval.entity_id),
                "approval_type": approval.approval_type,
                "title": approval.title,
                "description": approval.description,
                "payload": approval.payload,
                "status": approval.status.value if approval.status else None,
                "reviewer_notes": approval.reviewer_notes,
                "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
                "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
                "created_at": approval.created_at.isoformat() if approval.created_at else None,
            }
            for approval in approvals
        ],
        "total": db.query(ApprovalQueue).filter(ApprovalQueue.requested_by_user_id == current_user.id).count()
    }


@router.post("")
async def submit_for_approval(
    content_type: str,
    content_id: int,
    priority: int = 5,
    metadata: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit content for approval."""
    approval = ApprovalQueue(
        user_id=current_user.id,
        content_type=content_type,
        content_id=content_id,
        status="pending",
        submitted_by=current_user.email,
        priority=priority,
        metadata=metadata,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    
    return {
        "id": approval.id,
        "content_type": approval.content_type,
        "status": approval.status,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
    }


@router.get("/{approval_id}")
async def get_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific approval by ID."""
    approval = db.query(ApprovalQueue).filter(
        ApprovalQueue.id == approval_id,
        ApprovalQueue.user_id == current_user.id
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    return {
        "id": approval.id,
        "content_type": approval.content_type,
        "content_id": approval.content_id,
        "status": approval.status,
        "submitted_by": approval.submitted_by,
        "reviewed_by": approval.reviewed_by,
        "feedback": approval.feedback,
        "priority": approval.priority,
        "metadata": approval.metadata,
        "submitted_at": approval.submitted_at.isoformat() if approval.submitted_at else None,
        "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
    }


@router.post("/{approval_id}/approve")
async def approve_content(
    approval_id: int,
    feedback: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve content in the queue."""
    approval = db.query(ApprovalQueue).filter(
        ApprovalQueue.id == approval_id,
        ApprovalQueue.user_id == current_user.id
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail="Content already reviewed")
    
    approval.status = "approved"
    approval.reviewed_by = current_user.email
    approval.feedback = feedback
    
    db.commit()
    db.refresh(approval)
    
    return {
        "id": approval.id,
        "status": approval.status,
        "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
    }


@router.post("/{approval_id}/reject")
async def reject_content(
    approval_id: int,
    feedback: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject content in the queue."""
    approval = db.query(ApprovalQueue).filter(
        ApprovalQueue.id == approval_id,
        ApprovalQueue.user_id == current_user.id
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail="Content already reviewed")
    
    approval.status = "rejected"
    approval.reviewed_by = current_user.email
    approval.feedback = feedback
    
    db.commit()
    db.refresh(approval)
    
    return {
        "id": approval.id,
        "status": approval.status,
        "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
    }


@router.delete("/{approval_id}")
async def delete_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an approval queue item."""
    approval = db.query(ApprovalQueue).filter(
        ApprovalQueue.id == approval_id,
        ApprovalQueue.user_id == current_user.id
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    db.delete(approval)
    db.commit()
    
    return {"message": "Approval deleted successfully"}
