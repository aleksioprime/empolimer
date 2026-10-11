"""Как показывать значения: оценка относительно нормы и «сколько прошло». Без Qt - для тестов."""

from __future__ import annotations

from typing import Optional


def level(value: Optional[float], low: float, high: float) -> str:
    """unknown - нет значения, ok - в норме, low/high - ниже или выше нормы."""
    if value is None:
        return "unknown"
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "ok"


LEVEL_TEXT = {
    "unknown": "нет данных",
    "ok": "в норме",
    "low": "ниже нормы",
    "high": "выше нормы",
}


def ago(seconds: Optional[float]) -> str:
    if seconds is None:
        return "измерений ещё не было"
    seconds = max(0, int(seconds))
    if seconds < 5:
        return "только что"
    if seconds < 60:
        return f"{seconds} с назад"
    if seconds < 3600:
        return f"{seconds // 60} мин назад"
    return f"{seconds // 3600} ч {seconds % 3600 // 60} мин назад"


def is_stale(age: Optional[float], interval: Optional[float]) -> bool:
    """Данные устарели: три периода измерений без новых значений (не меньше двух минут)."""
    if age is None:
        return False
    return age > max(3 * (interval or 60), 120)
