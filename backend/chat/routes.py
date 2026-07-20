from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth.jwt import decode_access_token, get_current_user
from db import ChatMessage, User, get_db

from .connections import manager

router = APIRouter(tags=["chat"])


class UserSummary(BaseModel):
    id: str
    email: str
    role: str


class ChatMessageOut(BaseModel):
    id: str
    sender_id: str
    recipient_id: str
    body: str
    created_at: datetime


@router.get("/chat/users", response_model=list[UserSummary])
def list_users(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """All registered users except the caller, to start/continue a conversation with."""
    rows = db.query(User).filter(User.id != current_user["sub"]).order_by(User.email).all()
    return [UserSummary(id=u.id, email=u.email, role=u.role) for u in rows]


@router.get("/chat/messages/{other_user_id}", response_model=list[ChatMessageOut])
def get_conversation(
    other_user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full message history between the caller and one other user, oldest first."""
    me = current_user["sub"]
    rows = (
        db.query(ChatMessage)
        .filter(
            or_(
                (ChatMessage.sender_id == me) & (ChatMessage.recipient_id == other_user_id),
                (ChatMessage.sender_id == other_user_id) & (ChatMessage.recipient_id == me),
            )
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        ChatMessageOut(
            id=r.id, sender_id=r.sender_id, recipient_id=r.recipient_id,
            body=r.body, created_at=r.created_at,
        )
        for r in rows
    ]


@router.websocket("/chat/ws")
async def chat_ws(websocket: WebSocket, token: str):
    """
    Live chat socket. Auth token is passed as a query param (`?token=...`)
    since the browser WebSocket API cannot set an Authorization header.
    Client sends {"recipient_id": "...", "body": "..."} and receives the
    same shape back (from itself or the other party) as messages persist.
    """
    try:
        claims = decode_access_token(token)
    except HTTPException:
        await websocket.close(code=4401)
        return

    user_id = claims["sub"]
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            recipient_id = data.get("recipient_id")
            body = (data.get("body") or "").strip()
            if not recipient_id or not body:
                continue

            from db import get_session

            db = get_session()
            try:
                message = ChatMessage(sender_id=user_id, recipient_id=recipient_id, body=body)
                db.add(message)
                db.commit()
                payload = {
                    "id": message.id,
                    "sender_id": message.sender_id,
                    "recipient_id": message.recipient_id,
                    "body": message.body,
                    "created_at": message.created_at.isoformat(),
                }
            finally:
                db.close()

            await websocket.send_json(payload)
            await manager.send_to_user(recipient_id, payload)
    except WebSocketDisconnect:
        manager.disconnect(user_id)
