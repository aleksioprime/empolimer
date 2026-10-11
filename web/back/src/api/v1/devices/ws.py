from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette import status

from src.managers.ws import manager
from src.core.security import JWTBearer

router = APIRouter()


@router.websocket("/ws/")
async def websocket_devices(websocket: WebSocket):
    """
    Живое обновление списка устройств. Токен — в query-параметре token.
    Клиент может присылать "ping" — сервер ответит "pong".
    """
    token = websocket.query_params.get("token")
    user = JWTBearer.parse_token(token) if token else None
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
