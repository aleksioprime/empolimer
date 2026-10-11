"""
Оценка состояния устройства для мониторинга: на связи ли оно и что требует внимания.
Тексты проблем - для людей: что случилось и что проверить.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from src.core.config import settings
from src.models.device import Device, DeviceData
from src.schemas.device import DeviceProblem, Thresholds


def thresholds(device: Device) -> Thresholds:
    defaults = settings.monitoring
    pick = lambda value, default: default if value is None else value
    return Thresholds(
        temp_min=pick(device.temp_min, defaults.temp_min),
        temp_max=pick(device.temp_max, defaults.temp_max),
        hum_min=pick(device.hum_min, defaults.hum_min),
        hum_max=pick(device.hum_max, defaults.hum_max),
    )


def offline_after(status: dict) -> timedelta:
    """Без сообщений дольше трёх периодов измерений (но не меньше 5 минут) - нет связи."""
    try:
        interval = float(status.get("interval") or 60)
    except (TypeError, ValueError):
        interval = 60
    return max(settings.monitoring.offline_after, timedelta(seconds=3 * interval))


def is_online(device: Device, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    status = device.status or {}
    if device.last_seen is None or status.get("online") is False:
        return False
    return now - device.last_seen < offline_after(status)


def _range_problem(code: str, label: str, unit: str, value: Optional[float], low: float, high: float):
    if value is None:
        return None
    if value > high:
        return DeviceProblem(code=f"{code}_high", level="warning",
                             text=f"{label} выше нормы: {value:.1f} {unit} (норма до {high:g})")
    if value < low:
        return DeviceProblem(code=f"{code}_low", level="warning",
                             text=f"{label} ниже нормы: {value:.1f} {unit} (норма от {low:g})")
    return None


def evaluate(device: Device, last_data: Optional[DeviceData],
             now: Optional[datetime] = None) -> tuple[bool, str, list[DeviceProblem]]:
    """
    Возвращает (online, state, problems).
    state: new - данных ещё не было, offline - нет связи, warning - есть замечания, ok - всё в порядке.
    """
    now = now or datetime.now(timezone.utc)
    status = device.status or {}
    online = is_online(device, now)
    problems: list[DeviceProblem] = []

    if device.last_seen is None and last_data is None:
        problems.append(DeviceProblem(
            code="new", level="info",
            text="Данных ещё не было. Проверьте device.id и настройки mqtt в config.json на SD-карте"))
        return False, "new", problems

    if not online:
        problems.append(DeviceProblem(
            code="offline", level="error",
            text="Нет связи с устройством: проверьте питание и Wi-Fi. Данные сохраняются на SD-карту "
                 "и придут после восстановления связи"))

    if status.get("sensor") is False:
        problems.append(DeviceProblem(code="sensor", level="error",
                                      text="Датчик температуры и влажности не отвечает - проверьте провод"))
    if status.get("sd") is False:
        problems.append(DeviceProblem(code="sd", level="warning",
                                      text="SD-карта не найдена: при обрыве связи данные будут потеряны"))
    if status.get("config_error") and status.get("sd") is not False:
        problems.append(DeviceProblem(code="config", level="warning",
                                      text=f"Ошибка в config.json: {status['config_error']}"))
    if status.get("time") is False:
        problems.append(DeviceProblem(code="time", level="warning",
                                      text="Часы устройства не синхронизированы: время измерений ставит сервер"))
    queue = status.get("queue") or 0
    if online and isinstance(queue, (int, float)) and queue > 0:
        problems.append(DeviceProblem(code="queue", level="info",
                                      text=f"Устройство досылает накопленные измерения: {int(queue)}"))

    if last_data is not None and online:
        limits = thresholds(device)
        for problem in (
            _range_problem("temp", "Температура", "°C", last_data.temperature, limits.temp_min, limits.temp_max),
            _range_problem("hum", "Влажность", "%", last_data.humidity, limits.hum_min, limits.hum_max),
        ):
            if problem:
                problems.append(problem)

    if not online:
        state = "offline"
    elif any(p.level in ("error", "warning") for p in problems):
        state = "warning"
    else:
        state = "ok"
    return online, state, problems
