"""Разбор MQTT-сообщений устройств (форматы - docs/protocol.md)."""

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")

# Границы правдоподобных значений: за ними - сбой датчика, а не погода.
LIMITS = {"temp": (-60.0, 100.0), "hum": (0.0, 100.0), "bat": (0.0, 30.0)}
MAX_CLOCK_AHEAD = timedelta(minutes=10)
MAX_AGE = timedelta(days=366)


@dataclass
class Topic:
    device: str
    kind: str  # data | status


@dataclass
class Reading:
    timestamp: datetime
    temperature: Optional[float]
    humidity: Optional[float]
    battery: Optional[float]


def parse_topic(topic: str) -> Optional[Topic]:
    """<prefix>/<id>/data|status (prefix из config.json, обычно empolimer) и старый devices/<id>/air."""
    parts = topic.split("/")
    if len(parts) != 3 or not NAME_PATTERN.match(parts[1]):
        return None
    prefix, device, kind = parts
    if prefix == "devices":
        return Topic(device, "data") if kind == "air" else None
    if kind in ("data", "status"):
        return Topic(device, kind)
    return None


def _value(payload: dict, key: str) -> Optional[float]:
    try:
        value = float(payload.get(key))
    except (TypeError, ValueError):
        return None
    low, high = LIMITS[key]
    if math.isnan(value) or not low <= value <= high:
        return None
    return value


def parse_timestamp(payload: dict, now: datetime) -> datetime:
    """
    ts - unix-время (новые прошивки), datetime - ISO-строка (старые). Без времени,
    с явно неверным временем (часы устройства не установлены) - время приёма.
    """
    moment = None
    ts = payload.get("ts")
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        try:
            moment = datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            moment = None
    elif isinstance(payload.get("datetime"), str):
        try:
            moment = datetime.fromisoformat(payload["datetime"])
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
        except ValueError:
            moment = None
    if moment is None or moment > now + MAX_CLOCK_AHEAD or moment < now - MAX_AGE:
        return now
    return moment


def parse_reading(payload: dict, now: datetime) -> Optional[Reading]:
    reading = Reading(
        timestamp=parse_timestamp(payload, now),
        temperature=_value(payload, "temp"),
        humidity=_value(payload, "hum"),
        battery=_value(payload, "bat"),
    )
    if reading.temperature is None and reading.humidity is None:
        return None
    return reading
