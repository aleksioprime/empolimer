import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

SEND_TIMEOUT_S = 5


class ConnectionManager:
    """
    Открытые WebSocket-соединения. Соединение, которое не принимает данные, закрывается
    и не мешает остальным.
    """

    def __init__(self):
        self.connections: set[WebSocket] = set()
        self.wake = asyncio.Event()  # новый клиент — разослать состояние сразу, не дожидаясь цикла

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)
        self.wake.set()
        logger.info(f"[WS] Подключение {websocket.client} (всего: {len(self.connections)})")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.discard(websocket)
            logger.info(f"[WS] Отключение {websocket.client} (всего: {len(self.connections)})")

    async def _send(self, websocket: WebSocket, data: str):
        try:
            await asyncio.wait_for(websocket.send_text(data), timeout=SEND_TIMEOUT_S)
        except Exception:
            self.disconnect(websocket)
            try:
                await websocket.close()
            except Exception:
                pass

    async def broadcast(self, data: str):
        await asyncio.gather(*(self._send(ws, data) for ws in list(self.connections)))


manager = ConnectionManager()
