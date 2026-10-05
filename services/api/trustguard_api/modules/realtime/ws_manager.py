# services/api/trustguard_api/modules/realtime/ws_manager.py
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections subscribed to real-time threat
    and asynchronous job status streams.
    """
    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"[WS] Client connected for user {user_id}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"[WS] Client disconnected for user {user_id}")

    async def broadcast_to_user(self, user_id: str, event_data: dict):
        if user_id in self.active_connections:
            dead_connections = set()
            payload = json.dumps(event_data)
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    logger.warning(f"[WS] Failed to send to socket: {e}")
                    dead_connections.add(ws)
            for dead in dead_connections:
                self.disconnect(user_id, dead)

ws_manager = ConnectionManager()
