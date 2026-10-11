"""Настройки станции: файл station.conf рядом с программой и аргументы командной строки.

Аргументы важнее файла. Формат файла - строки "ключ = значение", # - комментарий.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "station.conf"


@dataclass
class Settings:
    port: str = "auto"            # auto - первый /dev/ttyUSB* или /dev/ttyACM*
    camera: str = "auto"          # auto | picamera | usb | none
    camera_size: str = "640x480"
    fps: int = 10                 # на Pi Zero больше 10 кадров не нужно
    fullscreen: bool = True
    temp_min: float = 18.0        # границы нормы: вне них значение подсвечивается
    temp_max: float = 28.0
    hum_min: float = 40.0
    hum_max: float = 70.0
    web_port: int = 8080          # веб-доступ к станции; 0 - выключен
    web_control: bool = True      # можно ли управлять подсветкой из браузера
    stream_fps: int = 5           # кадров в секунду в видео для браузера

    @property
    def frame_size(self) -> tuple[int, int]:
        width, _, height = self.camera_size.lower().partition("x")
        try:
            return max(int(width), 160), max(int(height), 120)
        except ValueError:
            return 640, 480


def _convert(name: str, raw: str):
    kind = {f.name: f.type for f in fields(Settings)}[name]
    if kind in ("bool", bool):
        return raw.strip().lower() in ("1", "yes", "true", "on", "да")
    if kind in ("int", int):
        return int(raw)
    if kind in ("float", float):
        return float(raw)
    return raw.strip()


def read_file(path: Path) -> dict:
    """Прочитать station.conf; неизвестные ключи и ошибки значений пропускаются."""
    values: dict = {}
    if not path.exists():
        return values
    known = {f.name for f in fields(Settings)}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        if key not in known:
            continue
        try:
            values[key] = _convert(key, raw)
        except ValueError:
            continue
    return values


def load(argv: Optional[list[str]] = None) -> Settings:
    parser = argparse.ArgumentParser(description="Станция ЕмПолимер: камера и показания ESP")
    parser.add_argument("--config", type=Path, default=DEFAULT_PATH, help="файл настроек")
    parser.add_argument("--port", help="порт ESP, например /dev/ttyUSB0 (по умолчанию auto)")
    parser.add_argument("--camera", choices=["auto", "picamera", "usb", "none"])
    parser.add_argument("--camera-size", dest="camera_size", help="размер кадра, например 640x480")
    parser.add_argument("--fps", type=int)
    parser.add_argument("--window", dest="fullscreen", action="store_false", default=None,
                        help="окно вместо полноэкранного режима")
    parser.add_argument("--web-port", dest="web_port", type=int, help="порт веб-доступа (0 - выключить)")
    args = parser.parse_args(argv)

    values = read_file(args.config)
    for name in ("port", "camera", "camera_size", "fps", "fullscreen", "web_port"):
        value = getattr(args, name)
        if value is not None:
            values[name] = value
    return Settings(**values)
