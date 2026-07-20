import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from auth.jwt import decode_access_token, require_broker
from db import AgentActivityEvent, get_session

from . import CHANNEL, REDIS_URL, serialize_event

logger = logging.getLogger("agent_activity")

router = APIRouter(tags=["agent-activity"])

DEFAULT_HISTORY_LIMIT = 100
MAX_HISTORY_LIMIT = 500


@router.get("/agent-activity")
def list_agent_activity(
    limit: int = Query(DEFAULT_HISTORY_LIMIT, le=MAX_HISTORY_LIMIT),
    submission_id: str | None = Query(None),
    current_user: dict = Depends(require_broker),
):
    """
    Recent AI background-processing events, newest first — the page's initial
    load before WS /agent-activity/ws starts streaming anything new live.

    submission_id: when set, scopes the feed to one applicant's pipeline
    (used by the lead detail page's pipeline stepper) instead of the global
    feed the AI Activity page shows.
    """
    session = get_session()
    try:
        query = session.query(AgentActivityEvent)
        if submission_id:
            query = query.filter(AgentActivityEvent.submission_id == submission_id)
        rows = query.order_by(AgentActivityEvent.created_at.desc()).limit(limit).all()
        return {"events": [serialize_event(r) for r in rows]}
    finally:
        session.close()


@router.websocket("/agent-activity/ws")
async def agent_activity_ws(websocket: WebSocket, token: str = Query(...)):
    """
    Live feed of AI background-processing events. Auth token is a query param
    (`?token=...`), same as /chat/ws, since the browser WebSocket API can't
    set an Authorization header. Subscribes to the same Redis channel
    agent_activity.emit() publishes to (see backend/agent_activity/__init__.py
    for why Redis pub/sub is the bridge — emit() runs inside Celery worker
    processes, not this FastAPI process) and forwards every message verbatim
    to the browser. Read-only: the client never sends anything meaningful
    back, unlike /chat/ws.
    """
    try:
        claims = decode_access_token(token)
    except Exception:
        await websocket.close(code=4401)
        return
    if claims.get("role") != "broker":
        await websocket.close(code=4403)
        return

    await websocket.accept()

    redis_client = aioredis.from_url(REDIS_URL)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL)

    async def forward_events():
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await websocket.send_text(message["data"].decode() if isinstance(message["data"], bytes) else message["data"])

    async def watch_disconnect():
        # receive_text() raises WebSocketDisconnect the moment the client
        # closes — this is the only way to notice that on a socket this
        # route otherwise never reads from, so forward_events() above can be
        # cancelled instead of leaking a subscription forever.
        while True:
            await websocket.receive_text()

    forward_task = asyncio.create_task(forward_events())
    watch_task = asyncio.create_task(watch_disconnect())
    try:
        done, pending = await asyncio.wait(
            {forward_task, watch_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        watch_task.cancel()
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.aclose()
        await redis_client.aclose()
