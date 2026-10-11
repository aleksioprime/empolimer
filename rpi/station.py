#!/usr/bin/env python3
"""Запуск станции ЕмПолимер: python3 station.py [--port /dev/ttyUSB0] [--window]."""

import logging
import signal
import sys

from PyQt5.QtWidgets import QApplication

from station import config
from station.camera import CameraThread
from station.serial_link import SerialLink
from station.ui import MainWindow


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = config.load()
    app = QApplication(sys.argv)
    # Ctrl+C в терминале закрывает окно штатно.
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    link = SerialLink(settings.port)
    camera = CameraThread(settings.camera, settings.frame_size, settings.fps)
    window = MainWindow(settings, link, camera)
    window.showFullScreen() if settings.fullscreen else window.show()
    link.start()
    camera.start()
    code = app.exec_()
    window.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
