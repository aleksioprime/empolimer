#!/usr/bin/env python3
"""Запуск станции ЕмПолимер: python3 station.py [--port /dev/ttyUSB0] [--window] [--web-port 8080]."""

import logging
import signal
import sys

from PyQt5.QtCore import QBuffer, QIODevice
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication

from station import config
from station.camera import CameraThread
from station.serial_link import SerialLink
from station.state import StationState
from station.ui import MainWindow
from station.web import WebServer


def encode_jpeg(image: QImage, quality: int = 75) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "JPEG", quality)
    return bytes(buffer.data())


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = config.load()
    app = QApplication(sys.argv)
    # Ctrl+C в терминале закрывает окно штатно.
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    link = SerialLink(settings.port)
    camera = CameraThread(settings.camera, settings.frame_size, settings.fps)

    # Общее состояние для веб-доступа: его заполняют те же сигналы, что и экран.
    state = StationState(settings, encode_jpeg)
    link.reading.connect(state.set_reading)
    link.status.connect(state.set_status)
    link.connection.connect(state.set_connection)
    camera.frame.connect(state.set_frame)
    camera.failed.connect(state.set_camera_failed)
    web = WebServer(state, settings.web_port, link.send, settings.stream_fps)

    window = MainWindow(settings, link, camera, web)
    window.showFullScreen() if settings.fullscreen else window.show()
    link.start()
    camera.start()
    web.start()
    code = app.exec_()
    window.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
