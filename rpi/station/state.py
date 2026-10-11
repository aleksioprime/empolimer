"""Общее состояние станции: его заполняют связь с ESP и камера, читает веб-сервер.

Модуль без Qt: кадр хранится как есть, а в JPEG его превращает переданная функция
encode — так веб-сервер и тесты не зависят от Qt.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from station import protocol, view
from station.config import Settings


class StationState:
    def __init__(self, settings: Settings, encode: Callable[[Any], bytes]):
        self._settings = settings
        self._encode = encode
        self._lock = threading.Lock()
        self._frame_ready = threading.Condition(self._lock)

        self._reading: Optional[protocol.Reading] = None
        self._reading_at: Optional[float] = None
        self._status: dict = {}
        self._connected = False
        self._link_detail = "Поиск ESP…"
        self._camera_ok = False
        self._camera_message = "Запуск камеры…"

        self._frame = None
        self._frame_id = 0
        self._jpeg: tuple[int, bytes] = (0, b"")

    # --- запись (из потока интерфейса) ---

    def set_reading(self, reading: protocol.Reading) -> None:
        with self._lock:
            self._reading = reading
            self._reading_at = time.monotonic()

    def set_status(self, status: protocol.Status) -> None:
        with self._lock:
            self._status = dict(status.raw)

    def set_connection(self, connected: bool, detail: str) -> None:
        with self._lock:
            self._connected = connected
            self._link_detail = detail
            if not connected:
                self._status = {}

    def set_frame(self, frame) -> None:
        with self._frame_ready:
            self._frame = frame
            self._frame_id += 1
            self._camera_ok = True
            self._camera_message = ""
            self._frame_ready.notify_all()

    def set_camera_failed(self, message: str) -> None:
        with self._lock:
            self._frame = None
            self._camera_ok = False
            self._camera_message = message

    # --- чтение (из потоков веб-сервера) ---

    def jpeg(self) -> tuple[int, Optional[bytes]]:
        """Последний кадр в JPEG: сжимается один раз, сколько бы зрителей ни было."""
        with self._lock:
            frame, frame_id = self._frame, self._frame_id
            if frame is None:
                return frame_id, None
            if self._jpeg[0] == frame_id:
                return self._jpeg
        data = self._encode(frame)  # вне блокировки: сжатие не задерживает камеру
        with self._lock:
            if frame_id >= self._jpeg[0]:
                self._jpeg = (frame_id, data)
        return frame_id, data

    def wait_frame(self, after_id: int, timeout: float) -> bool:
        """Ждать кадр новее after_id; False — не дождались."""
        with self._frame_ready:
            return self._frame_ready.wait_for(lambda: self._frame_id > after_id, timeout)

    def snapshot(self) -> dict:
        s = self._settings
        with self._lock:
            reading, reading_at, status = self._reading, self._reading_at, dict(self._status)
            connected, detail = self._connected, self._link_detail
            camera_ok, camera_message = self._camera_ok, self._camera_message

        age = None if reading_at is None else time.monotonic() - reading_at
        temperature = reading.temperature if reading else None
        humidity = reading.humidity if reading else None
        return {
            "esp": {"connected": connected, "detail": detail},
            "reading": {
                "temperature": temperature,
                "humidity": humidity,
                "battery": reading.battery if reading else None,
                "age": None if age is None else round(age, 1),
                "stale": view.is_stale(age, status.get("interval")),
            },
            "levels": {
                "temperature": view.level(temperature, s.temp_min, s.temp_max),
                "humidity": view.level(humidity, s.hum_min, s.hum_max),
            },
            "thresholds": {
                "temp_min": s.temp_min, "temp_max": s.temp_max,
                "hum_min": s.hum_min, "hum_max": s.hum_max,
            },
            "status": status,
            "camera": {"ok": camera_ok, "message": camera_message},
            "control": s.web_control,
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
