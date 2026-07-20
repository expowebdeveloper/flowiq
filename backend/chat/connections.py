from fastapi import WebSocket


class ConnectionManager:
    """Tracks one live WebSocket per user_id and routes messages to online recipients."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: dict) -> bool:
        websocket = self._connections.get(user_id)
        if websocket is None:
            return False
        await websocket.send_json(payload)
        return True


manager = ConnectionManager()
