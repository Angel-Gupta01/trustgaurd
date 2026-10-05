# services/api/trustguard_api/modules/realtime/router.py
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from trustguard_api.core.security import decode_access_token
from trustguard_api.modules.realtime.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Realtime WebSocket"])

@router.websocket("/updates")
async def websocket_updates(
    websocket: WebSocket,
    token: str = Query(..., description="Bearer JWT access token for auth")
):
    """
    Real-time push event stream for deepfake job completion,
    blockchain confirmation depths, and unified risk alerts.
    """
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = str(payload["sub"])
    await ws_manager.connect(user_id, websocket)

    try:
        while True:
            # Keep-alive ping/pong and client filter subscriptions
            data = await websocket.receive_text()
            logger.debug(f"[WS] Inbound message from {user_id}: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)
