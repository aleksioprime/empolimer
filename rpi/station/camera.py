"""Камера в отдельном потоке: модуль камеры Raspberry (Picamera2) или USB-камера (OpenCV).

Если камера не найдена или отвалилась, поток пробует снова раз в несколько секунд,
а интерфейс показывает надпись вместо картинки — показания ESP при этом работают.
"""

from __future__ import annotations

import logging
import time

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

LOG = logging.getLogger(__name__)
RETRY_S = 5


class PiCamera:
    def __init__(self, size: tuple[int, int]):
        from picamera2 import Picamera2  # есть только на Raspberry: python3-picamera2

        self._camera = Picamera2()
        # RGB888 в Picamera2 — байты в порядке B, G, R.
        config = self._camera.create_preview_configuration(main={"format": "RGB888", "size": size})
        self._camera.configure(config)
        self._camera.start()

    def frame(self) -> QImage:
        array = self._camera.capture_array("main")
        height, width, _ = array.shape
        return QImage(array.data, width, height, array.strides[0], QImage.Format_BGR888).copy()

    def close(self) -> None:
        self._camera.close()


class UsbCamera:
    def __init__(self, size: tuple[int, int], index: int = 0):
        import cv2  # python3-opencv

        self._cv2 = cv2
        self._capture = cv2.VideoCapture(index)
        if not self._capture.isOpened():
            raise RuntimeError("USB-камера не найдена")
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])

    def frame(self) -> QImage:
        ok, array = self._capture.read()
        if not ok:
            raise RuntimeError("USB-камера не отдаёт кадры")
        height, width, _ = array.shape
        return QImage(array.data, width, height, array.strides[0], QImage.Format_BGR888).copy()

    def close(self) -> None:
        self._capture.release()


def open_camera(kind: str, size: tuple[int, int]):
    """kind: auto | picamera | usb. auto пробует модуль камеры, затем USB."""
    errors = []
    for candidate in (["picamera", "usb"] if kind == "auto" else [kind]):
        try:
            return PiCamera(size) if candidate == "picamera" else UsbCamera(size)
        except Exception as exc:  # библиотеки нет или камера не подключена
            errors.append(f"{candidate}: {exc}")
    raise RuntimeError("; ".join(errors))


class CameraThread(QThread):
    frame = pyqtSignal(QImage)
    failed = pyqtSignal(str)

    def __init__(self, kind: str, size: tuple[int, int], fps: int):
        super().__init__()
        self._kind = kind
        self._size = size
        self._period = 1.0 / max(1, fps)
        self._running = True

    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    def run(self) -> None:
        if self._kind == "none":
            self.failed.emit("Камера отключена в настройках")
            return
        while self._running:
            try:
                camera = open_camera(self._kind, self._size)
            except RuntimeError as exc:
                LOG.warning("Камера: %s", exc)
                self.failed.emit("Камера не подключена")
                self._sleep(RETRY_S)
                continue
            try:
                while self._running:
                    started = time.monotonic()
                    self.frame.emit(camera.frame())
                    self._sleep(self._period - (time.monotonic() - started))
            except Exception as exc:
                LOG.warning("Камера остановилась: %s", exc)
                self.failed.emit("Камера не отвечает, переподключение…")
            finally:
                camera.close()

    def _sleep(self, seconds: float) -> None:
        """Пауза, которую прерывает stop()."""
        end = time.monotonic() + seconds
        while self._running:
            left = end - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(0.1, left))
