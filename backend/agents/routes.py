from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["agent"])


class AgentRequest(BaseModel):
    email: str
    task: Optional[str] = None  # custom instruction, or leave empty for default


@router.post("/agent/run")
def run_agent(req: AgentRequest):
    """Trigger the email agent to read and reply to emails (runs in background via Celery)."""
    from celery_app import run_email_agent_task
    job = run_email_agent_task.delay(req.email, req.task)
    return {"task_id": job.id, "status": "started", "message": "Agent is running in background."}


@router.get("/agent/status/{task_id}")
def agent_status(task_id: str):
    """Check the status of a running agent task."""
    from celery_app import celery
    job = celery.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": job.status,
        "result": job.result if job.ready() else None,
    }
