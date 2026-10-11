"""Протокол обмена с ESP по USB: по строке на сообщение (docs/protocol.md).

ESP → Raspberry: JSON {"type": "data" | "status" | "ack", ...} и журнал "# ...".
Raspberry → ESP: текстовые команды "LIGHT ON", "TIME 1760000000" и т. п.
Модуль без Qt и без порта, чтобы его можно было проверять тестами.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class Reading:
    """Измерение датчика."""

    temperature: float
    humidity: float
    battery: Optional[float] = None
    ts: Optional[int] = None  # unix-время ESP; None - часы ESP ещё не установлены


@dataclass
class Status:
    """Состояние ESP: связь, SD, датчик, подсветка. Неизвестные поля - в raw."""

    raw: dict = field(default_factory=dict)

    def get(self, key: str, default=None):
        return self.raw.get(key, default)


@dataclass
class Ack:
    command: str
    ok: bool
    error: str = ""


@dataclass
class Log:
    text: str


Message = Union[Reading, Status, Ack, Log]


def _number(value) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def parse_line(line: str) -> Optional[Message]:
    """Разобрать строку от ESP. Мусор (например, вывод загрузчика ESP8266) - None."""
    line = line.strip()
    if not line:
        return None
    if line.startswith("#"):
        return Log(line.lstrip("# ").strip())
    if not line.startswith("{"):
        return None
    try:
        payload = json.loads(line)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None

    kind = payload.get("type")
    if kind == "data":
        temperature = _number(payload.get("temp"))
        humidity = _number(payload.get("hum"))
        if temperature is None or humidity is None:
            return None
        ts = payload.get("ts")
        return Reading(
            temperature=temperature,
            humidity=humidity,
            battery=_number(payload.get("bat")),
            ts=int(ts) if isinstance(ts, (int, float)) else None,
        )
    if kind == "status":
        return Status(raw=payload)
    if kind == "ack":
        return Ack(
            command=str(payload.get("cmd", "")),
            ok=bool(payload.get("ok")),
            error=str(payload.get("error", "")),
        )
    return None


def light_command(mode: str, brightness: Optional[int] = None) -> str:
    """Команда подсветки: mode - on, off или auto."""
    mode = mode.lower()
    if mode == "on":
        return "LIGHT ON" if brightness is None else f"LIGHT ON {max(0, min(255, int(brightness)))}"
    if mode == "off":
        return "LIGHT OFF"
    if mode == "auto":
        return "LIGHT AUTO"
    raise ValueError(f"Неизвестный режим подсветки: {mode}")


def time_command(epoch: float) -> str:
    return f"TIME {int(epoch)}"
