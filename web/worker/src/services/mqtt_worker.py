import asyncio
import json
import os
import time
from datetime import datetime, timezone

from aiomqtt import Client, MqttError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import settings
from src.core.logger import logger
from src.db.postgres import session_factory
from src.models.device import Device, DeviceData
from src.utils.parse import parse_reading, parse_topic

RECONNECT_MIN_S = 2
RECONNECT_MAX_S = 60
DB_ATTEMPTS = 3
HEARTBEAT_S = 20


class MQTTWorker:
    """
    Принимает сообщения устройств из MQTT и сохраняет в PostgreSQL.
    Переживает перезапуск брокера и базы: переподключается сам, сообщение при
    недоступной базе повторяет несколько раз.
    """

    def __init__(self):
        self.connected = False
        self._should_run = True

    async def start(self):
        heartbeat = asyncio.create_task(self._heartbeat())
        delay = RECONNECT_MIN_S
        mqtt = settings.mqtt
        logger.info(f"MQTT worker: {mqtt.broker}:{mqtt.port}, топики {mqtt.topics}")
        try:
            while self._should_run:
                try:
                    async with Client(
                        hostname=mqtt.broker,
                        port=mqtt.port,
                        username=mqtt.username or None,
                        password=mqtt.password or None,
                        identifier=f"empolimer-worker-{os.getpid()}",
                    ) as client:
                        for topic in mqtt.topics:
                            await client.subscribe(topic, qos=1)
                        logger.info("Подключено к брокеру, подписки оформлены")
                        self.connected = True
                        delay = RECONNECT_MIN_S
                        async for message in client.messages:
                            await self.process_message(message.topic.value, message.payload)
                except MqttError as e:
                    logger.error(f"MQTT: {e}. Переподключение через {delay} с")
                finally:
                    self.connected = False
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_S)
        finally:
            heartbeat.cancel()

    def stop(self):
        self._should_run = False

    async def process_message(self, topic_name: str, raw: bytes):
        topic = parse_topic(topic_name)
        if topic is None:
            logger.warning(f"Неизвестный топик: {topic_name}")
            return
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("ожидается JSON-объект")
        except ValueError as e:
            logger.warning(f"{topic_name}: не JSON ({e})")
            return

        for attempt in range(1, DB_ATTEMPTS + 1):
            try:
                await self._save(topic.device, topic.kind, payload)
                return
            except SQLAlchemyError as e:
                logger.error(f"{topic_name}: ошибка базы ({e.__class__.__name__}), попытка {attempt}/{DB_ATTEMPTS}")
                await asyncio.sleep(attempt * 2)
        logger.error(f"{topic_name}: сообщение не сохранено: {payload}")

    async def _save(self, name: str, kind: str, payload: dict):
        now = datetime.now(timezone.utc)
        async with session_factory() as session:
            device = await self._device(session, name)
            if device is None:
                logger.warning(f"Устройство «{name}» не зарегистрировано - добавьте его в веб-интерфейсе")
                return

            if kind == "status":
                device.status = {**(device.status or {}), **payload, "received_at": now.isoformat()}
                # {"online": false} публикует брокер после обрыва - это не контакт с устройством.
                if payload.get("online") is not False:
                    device.last_seen = now
                await session.commit()
                logger.info(f"{name}: статус {'онлайн' if payload.get('online') is not False else 'офлайн'}")
                return

            reading = parse_reading(payload, now)
            device.last_seen = now
            if reading is None:
                await session.commit()
                logger.warning(f"{name}: в измерении нет правдоподобных значений: {payload}")
                return
            await session.execute(
                insert(DeviceData).values(
                    device_id=device.id,
                    timestamp=reading.timestamp,
                    temperature=reading.temperature,
                    humidity=reading.humidity,
                    battery=reading.battery,
                ).on_conflict_do_nothing(index_elements=["device_id", "timestamp"])
            )
            await session.commit()
            logger.info(f"{name}: {reading.timestamp:%Y-%m-%d %H:%M:%S%z} t={reading.temperature} h={reading.humidity}")

    async def _device(self, session, name: str):
        if settings.auto_register:
            await session.execute(insert(Device).values(name=name).on_conflict_do_nothing(index_elements=["name"]))
        return await session.scalar(select(Device).where(Device.name == name))

    async def _heartbeat(self):
        """Файл для healthcheck контейнера: обновляется, пока есть связь с брокером."""
        while True:
            if self.connected:
                try:
                    with open(settings.heartbeat_file, "w") as f:
                        f.write(str(int(time.time())))
                except OSError:
                    pass
            await asyncio.sleep(HEARTBEAT_S)
