# backend/app/api/agents.py — Agent task and run management
# Cost classification: FREE + OPEN SOURCE

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.agent_task import AgentTask
from app.models.agent_run import AgentRun

router = APIRouter()


@router.get("/tasks")
async def list_agent_tasks(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all agent tasks. No user filtering - returns all tasks."""
    query = db.query(AgentTask)
    
    if status:
        query = query.filter(AgentTask.status == status)
    
    tasks = query.offset(skip).limit(limit).all()
    
    return {
        "tasks": [
            {
                "id": str(task.id),
                "run_id": str(task.run_id),
                "task_name": task.task_name,
                "task_order": task.task_order,
                "input_data": task.input_data,
                "output_data": task.output_data,
                "decision_log": task.decision_log,
                "status": task.status.value if task.status else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "finished_at": task.finished_at.isoformat() if task.finished_at else None,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            for task in tasks
        ],
        "total": db.query(AgentTask).count()
    }


@router.post("/tasks")
async def create_agent_task(
    task_type: str,
    input_data: dict,
    priority: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new agent task."""
    task = AgentTask(
        user_id=current_user.id,
        task_type=task_type,
        status="pending",
        priority=priority,
        input_data=input_data,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.get("/tasks/{task_id}")
async def get_agent_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific agent task by ID."""
    task = db.query(AgentTask).filter(
        AgentTask.id == task_id,
        AgentTask.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "priority": task.priority,
        "input_data": task.input_data,
        "result_data": task.result_data,
        "error_message": task.error_message,
        "progress": task.progress,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.delete("/tasks/{task_id}")
async def cancel_agent_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel/delete an agent task."""
    task = db.query(AgentTask).filter(
        AgentTask.id == task_id,
        AgentTask.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status == "running":
        task.status = "cancelled"
        db.commit()
        return {"message": "Task cancelled"}
    else:
        db.delete(task)
        db.commit()
        return {"message": "Task deleted"}


@router.get("/runs")
async def list_agent_runs(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all agent runs. No user filtering - returns all runs."""
    query = db.query(AgentRun)
    
    if status:
        query = query.filter(AgentRun.status == status)
    
    runs = query.offset(skip).limit(limit).all()
    
    return {
        "runs": [
            {
                "id": str(run.id),
                "agent_name": run.agent_name,
                "run_type": run.run_type,
                "input_summary": run.input_summary,
                "output_summary": run.output_summary,
                "decision_log": run.decision_log,
                "status": run.status.value if run.status else None,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "duration_seconds": run.duration_seconds,
                "error_message": run.error_message,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "results": run.results,
                "error_message": run.error_message,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
            for run in runs
        ],
        "total": db.query(AgentRun).count()
    }


@router.get("/runs/{run_id}")
async def get_agent_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific agent run by ID."""
    run = db.query(AgentRun).filter(
        AgentRun.id == run_id,
        AgentRun.user_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "id": run.id,
        "agent_name": run.agent_name,
        "status": run.status,
        "trigger": run.trigger,
        "actions_taken": run.actions_taken,
        "results": run.results,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
