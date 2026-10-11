"""Связь с ESP по USB в отдельном потоке: чтение сообщений, команды, переподключение."""

from __future__ import annotations

import glob
import logging
import queue
import subprocess
import threading
import time
from typing import Optional

import serial
from PyQt5.QtCore import QObject, pyqtSignal

from station import protocol

LOG = logging.getLogger(__name__)

BAUD = 115200
RECONNECT_S = 3
TIME_SYNC_S = 3600


def find_port() -> Optional[str]:
    """Первый USB-последовательный порт: NodeMCU и ESP32 DevKit - ttyUSB, платы с нативным USB - ttyACM."""
    ports = sorted(glob.glob("/dev/ttyUSB*")) + sorted(glob.glob("/dev/ttyACM*"))
    return ports[0] if ports else None


def clock_synced() -> bool:
    """Часы Raspberry синхронизированы по сети. Без интернета у Raspberry нет верного времени."""
    try:
        result = subprocess.run(
            ["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
            capture_output=True, text=True, timeout=2,
        )
        return result.stdout.strip() == "yes"
    except (OSError, subprocess.SubprocessError):
        return False


class SerialLink(QObject):
    """Сигналы приходят из рабочего потока; Qt доставляет их в поток интерфейса."""

    reading = pyqtSignal(object)          # protocol.Reading
    status = pyqtSignal(object)           # protocol.Status
    ack = pyqtSignal(object)              # protocol.Ack
    connection = pyqtSignal(bool, str)    # подключено, порт или причина ошибки

    def __init__(self, port: str = "auto"):
        super().__init__()
        self._port_setting = port
        self._commands: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="serial-link", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    def send(self, command: str) -> None:
        """Поставить команду в очередь; без связи она уйдёт после подключения."""
        self._commands.put(command)

    def _run(self) -> None:
        while not self._stop.is_set():
            port = find_port() if self._port_setting == "auto" else self._port_setting
            if not port:
                self.connection.emit(False, "ESP не найдена: подключите USB-кабель")
                self._stop.wait(RECONNECT_S)
                continue
            try:
                self._session(port)
            except (serial.SerialException, OSError) as exc:
                LOG.warning("Порт %s: %s", port, exc)
                self.connection.emit(False, f"Нет связи с ESP ({port})")
            self._stop.wait(RECONNECT_S)

    def _open(self, port: str) -> serial.Serial:
        # DTR и RTS выключены до открытия: иначе NodeMCU и ESP32 перезагружаются при каждом подключении.
        link = serial.Serial()
        link.port = port
        link.baudrate = BAUD
        link.timeout = 0.5
        link.dtr = False
        link.rts = False
        link.open()
        return link

    def _session(self, port: str) -> None:
        with self._open(port) as link:
            LOG.info("ESP подключена: %s", port)
            self.connection.emit(True, port)
            last_time_sync = 0.0
            self.send("STATUS")
            buffer = b""
            while not self._stop.is_set():
                if time.monotonic() - last_time_sync > TIME_SYNC_S and clock_synced():
                    link.write((protocol.time_command(time.time()) + "\n").encode())
                    last_time_sync = time.monotonic()
                while not self._commands.empty():
                    link.write((self._commands.get_nowait() + "\n").encode())

                buffer += link.read(link.in_waiting or 1)
                *lines, buffer = buffer.split(b"\n")
                if len(buffer) > 4096:  # строка без конца - мусор
                    buffer = b""
                for raw in lines:
                    self._dispatch(raw.decode("utf-8", errors="replace"))

    def _dispatch(self, line: str) -> None:
        message = protocol.parse_line(line)
        if isinstance(message, protocol.Reading):
            self.reading.emit(message)
        elif isinstance(message, protocol.Status):
            self.status.emit(message)
        elif isinstance(message, protocol.Ack):
            if not message.ok:
                LOG.warning("ESP отклонила «%s»: %s", message.command, message.error)
            self.ack.emit(message)
        elif isinstance(message, protocol.Log):
            LOG.info("ESP: %s", message.text)
