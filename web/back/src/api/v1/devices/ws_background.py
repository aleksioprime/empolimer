import asyncio
import logging
import json
import time

from src.managers.ws import manager
from src.dependencies.device import get_device_service
from src.dependencies.uow import get_unit_of_work

logger = logging.getLogger(__name__)

CHECK_INTERVAL_S = 5
HEARTBEAT_S = 30  # даже без изменений клиенты получают данные — так они видят, что связь жива


async def periodic_broadcast():
    """
    Рассылает список устройств клиентам WebSocket: при изменениях, при подключении
    нового клиента и не реже раза в HEARTBEAT_S секунд.
    """
    last_payload = None
    last_sent = 0.0
    while True:
        try:
            await asyncio.wait_for(manager.wake.wait(), timeout=CHECK_INTERVAL_S)
        except asyncio.TimeoutError:
            pass
        forced = manager.wake.is_set()
        manager.wake.clear()
        if not manager.connections:
            continue

        try:
            service = await get_device_service(uow=await get_unit_of_work())
            devices = await service.get_all()
            payload = json.dumps({
                "type": "devices_update",
                "devices": [device.model_dump(mode="json") for device in devices],
            }, ensure_ascii=False)
            if forced or payload != last_payload or time.monotonic() - last_sent > HEARTBEAT_S:
                await manager.broadcast(payload)
                last_payload, last_sent = payload, time.monotonic()
        except Exception:
            logger.exception("WebSocket: ошибка рассылки")
