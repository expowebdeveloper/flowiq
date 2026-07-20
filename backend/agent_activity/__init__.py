import json
import logging

import redis

from db import AgentActivityEvent, get_session

logger = logging.getLogger("agent_activity")

REDIS_URL = "redis://localhost:6379/0"
CHANNEL = "agent_activity_events"

# One connection reused for every publish — emit() is called from inside
# Celery task bodies (a different OS process than the FastAPI/uvicorn
# process holding live WebSocket connections), so a plain in-memory broadcast
# like chat/connections.py's ConnectionManager can't reach across processes.
# Redis pub/sub is already present in this app (Celery's own broker), so it's
# reused here as the cross-process bridge: emit() publishes, and
# agent_activity/routes.py's WS route subscribes and fans out to browsers.
_redis_client = redis.Redis.from_url(REDIS_URL)


def emit(
    source: str,
    status: str,
    message: str,
    submission_id: str | None = None,
    detail: dict | None = None,
) -> None:
    """
    Records one AI-background-processing step: persists it (so the activity
    feed has history on page load) and publishes it over Redis pub/sub (so
    any open WS /agent-activity/ws connections see it immediately).

    source: which pipeline stage produced this event, e.g. "mailbox_poll",
    "document_processing", "email_agent", "bank_notify".
    status: "started" | "info" | "success" | "error".
    Failures here are logged and swallowed — a broken activity feed should
    never take down the actual email/OCR/agent pipeline it's observing.
    """
    session = get_session()
    try:
        event = AgentActivityEvent(
            source=source,
            status=status,
            message=message,
            submission_id=submission_id,
            detail=json.dumps(detail) if detail is not None else None,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        payload = serialize_event(event)
    except Exception:
        logger.exception("agent_activity: failed to persist event (source=%s, message=%s)", source, message)
        return
    finally:
        session.close()

    try:
        _redis_client.publish(CHANNEL, json.dumps(payload))
    except Exception:
        logger.exception("agent_activity: failed to publish event to redis (source=%s)", source)


def serialize_event(event: AgentActivityEvent) -> dict:
    return {
        "id": event.id,
        "created_at": event.created_at.isoformat(),
        "source": event.source,
        "status": event.status,
        "message": event.message,
        "submission_id": event.submission_id,
        "detail": json.loads(event.detail) if event.detail else None,
    }
