"""Экран станции: слева камера, справа показания ESP, состояние модулей и подсветка."""

from __future__ import annotations

import time
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QKeySequence, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton, QShortcut,
    QSizePolicy, QVBoxLayout, QWidget,
)

from station import protocol, view
from station.config import Settings

COLORS = {"ok": "#3fb950", "low": "#58a6ff", "high": "#f0883e", "unknown": "#6e7681"}

STYLE = """
QWidget { background: #0d1117; color: #e6edf3; font-family: "DejaVu Sans", sans-serif; }
QLabel#title { font-size: 20px; font-weight: bold; }
QLabel#muted { color: #8b949e; font-size: 13px; }
QLabel#camera { background: #010409; color: #8b949e; font-size: 18px; }
QFrame#card { background: #161b22; border: 2px solid #30363d; border-radius: 12px; }
QLabel#cardLabel { color: #8b949e; font-size: 14px; background: transparent; }
QLabel#cardValue { font-size: 40px; font-weight: bold; background: transparent; }
QLabel#cardHint { font-size: 13px; background: transparent; }
QLabel#banner { border-radius: 8px; padding: 6px 10px; font-size: 14px; }
QPushButton { background: #21262d; border: 1px solid #30363d; border-radius: 10px;
              font-size: 16px; padding: 10px; min-height: 28px; }
QPushButton:checked { background: #238636; border-color: #2ea043; }
QPushButton:pressed { background: #30363d; }
QFrame#web { background: #161b22; border: 1px solid #30363d; border-radius: 10px; }
QFrame#web:hover { border-color: #8b949e; }
QLabel#webTitle { font-size: 14px; background: transparent; }
QLabel#webDetail { color: #8b949e; font-size: 12px; background: transparent; }
QDialog { background: #0d1117; }
QLabel#qrUrl { font-size: 22px; font-weight: bold; }
"""

WEB_STATES = {
    "ok": ("#3fb950", "Веб-доступ работает"),
    "starting": ("#6e7681", "Веб-доступ запускается…"),
    "error": ("#f85149", "Веб-доступ не работает"),
    "disabled": ("#6e7681", "Веб-доступ выключен"),
}


def qr_pixmap(text: str, size: int) -> Optional[QPixmap]:
    """QR-код адреса станции; None, если нет библиотеки qrcode (python3-qrcode)."""
    try:
        import qrcode
    except ImportError:
        return None
    code = qrcode.QRCode(border=2)
    code.add_data(text)
    matrix = code.get_matrix()
    cells = len(matrix)
    scale = max(1, size // cells)
    pixmap = QPixmap(cells * scale, cells * scale)
    pixmap.fill(Qt.white)
    painter = QPainter(pixmap)
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                painter.fillRect(x * scale, y * scale, scale, scale, QColor("black"))
    painter.end()
    return pixmap


class WebDialog(QDialog):
    """Адрес станции крупно и QR-код — чтобы открыть страницу с телефона."""

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Веб-доступ к станции")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        urls = info.get("urls") or []
        if info.get("state") == "ok" and urls:
            title = QLabel("Откройте на телефоне или компьютере в той же сети:")
            layout.addWidget(title)
            pixmap = qr_pixmap(urls[0], 280)
            if pixmap:
                qr = QLabel()
                qr.setPixmap(pixmap)
                qr.setAlignment(Qt.AlignCenter)
                layout.addWidget(qr)
            for index, url in enumerate(urls):
                label = QLabel(url, objectName="qrUrl" if index == 0 else "muted")
                label.setAlignment(Qt.AlignCenter)
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                layout.addWidget(label)
            viewers = QLabel(f"Смотрят видео: {info.get('viewers', 0)} · подключено: {info.get('clients', 0)}",
                             objectName="muted")
            viewers.setAlignment(Qt.AlignCenter)
            layout.addWidget(viewers)
        else:
            _, text = WEB_STATES.get(info.get("state"), WEB_STATES["error"])
            message = text + (f": {info['error']}" if info.get("error") else "")
            if info.get("state") == "disabled":
                message += ". Включите web_port в station.conf"
            layout.addWidget(QLabel(message))
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        layout.addWidget(close)


class WebRow(QFrame):
    """Строка «Веб-доступ»: состояние сервера, адрес и подключённые; по нажатию — QR-код."""

    clicked = pyqtSignal()

    def __init__(self):
        super().__init__(objectName="web")
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(0)
        self._title = QLabel("", objectName="webTitle")
        self._detail = QLabel("", objectName="webDetail")
        layout.addWidget(self._title)
        layout.addWidget(self._detail)

    def show_info(self, info: dict) -> None:
        state = info.get("state", "disabled")
        color, text = WEB_STATES.get(state, WEB_STATES["error"])
        self._title.setText(f"<span style='color:{color}'>●</span> {text}")
        if state == "ok":
            url = (info.get("urls") or [""])[0].replace("http://", "")
            people = info.get("clients", 0)
            watching = info.get("viewers", 0)
            who = f"подключено: {people}" + (f", смотрят видео: {watching}" if watching else "") if people else "никто не подключён"
            self._detail.setText(f"{url} · {who}")
        elif state == "error":
            self._detail.setText(info.get("error") or "")
        else:
            self._detail.setText("")

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class MetricCard(QFrame):
    def __init__(self, label: str, unit: str, digits: int = 1):
        super().__init__()
        self.setObjectName("card")
        self._unit = unit
        self._digits = digits
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        self._label = QLabel(label, objectName="cardLabel")
        self._value = QLabel("—", objectName="cardValue")
        self._hint = QLabel("", objectName="cardHint")
        for widget in (self._label, self._value, self._hint):
            layout.addWidget(widget)

    def show_value(self, value: Optional[float], state: str, hint: str) -> None:
        color = COLORS[state]
        self._value.setText("—" if value is None else f"{value:.{self._digits}f} {self._unit}")
        self._value.setStyleSheet(f"color: {color};")
        self._hint.setText(hint)
        self._hint.setStyleSheet(f"color: {color};")
        self.setStyleSheet(f"QFrame#card {{ border-color: {color if state != 'ok' else '#30363d'}; }}")


class Indicator(QLabel):
    def __init__(self, name: str):
        super().__init__()
        self._name = name
        self.set(None)

    def set(self, ok: Optional[bool], detail: str = "") -> None:
        color = COLORS["unknown"] if ok is None else (COLORS["ok"] if ok else "#f85149")
        text = f"<span style='color:{color}'>●</span> {self._name}"
        if detail:
            text += f" <span style='color:#8b949e'>{detail}</span>"
        self.setText(text)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, link, camera, web=None):
        super().__init__()
        self._settings = settings
        self._link = link
        self._camera = camera
        self._web = web
        self._pixmap: Optional[QPixmap] = None
        self._reading: Optional[protocol.Reading] = None
        self._reading_at: Optional[float] = None
        self._status = protocol.Status()
        self._connected = False

        self.setWindowTitle("ЕмПолимер — станция")
        self.setStyleSheet(STYLE)
        self.setCentralWidget(self._build())
        self.setMinimumSize(640, 400)

        link.reading.connect(self._on_reading)
        link.status.connect(self._on_status)
        link.connection.connect(self._on_connection)
        camera.frame.connect(self._on_frame)
        camera.failed.connect(self._on_camera_failed)

        self._ticker = QTimer(self)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start(1000)

        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)
        QShortcut(QKeySequence("F11"), self, activated=self._toggle_fullscreen)
        self._on_connection(False, "Поиск ESP…")
        self._render()
        self._render_web()

    # --- построение экрана ---

    def _build(self) -> QWidget:
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self._camera_view = QLabel("Запуск камеры…", objectName="camera")
        self._camera_view.setAlignment(Qt.AlignCenter)
        self._camera_view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self._camera_view, stretch=3)

        panel = QVBoxLayout()
        panel.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(QLabel("ЕмПолимер", objectName="title"))
        header.addStretch()
        self._clock = QLabel("", objectName="muted")
        header.addWidget(self._clock)
        panel.addLayout(header)

        self._device = QLabel("", objectName="muted")
        panel.addWidget(self._device)
        self._banner = QLabel("", objectName="banner")
        self._banner.setWordWrap(True)
        panel.addWidget(self._banner)

        self._temperature = MetricCard("Температура", "°C")
        self._humidity = MetricCard("Влажность", "%")
        self._battery = MetricCard("Батарея", "В", digits=2)
        for card in (self._temperature, self._humidity, self._battery):
            panel.addWidget(card)

        self._updated = QLabel("", objectName="muted")
        panel.addWidget(self._updated)

        grid = QGridLayout()
        grid.setVerticalSpacing(4)
        self._indicators = {
            "wifi": Indicator("Wi-Fi"), "mqtt": Indicator("Сервер"),
            "sd": Indicator("SD-карта"), "time": Indicator("Часы"),
        }
        for index, widget in enumerate(self._indicators.values()):
            grid.addWidget(widget, index // 2, index % 2)
        panel.addLayout(grid)

        self._web_row = WebRow()
        self._web_row.clicked.connect(self._show_web_dialog)
        panel.addWidget(self._web_row)

        panel.addStretch()
        self._light_state = QLabel("Подсветка", objectName="muted")
        panel.addWidget(self._light_state)
        buttons = QHBoxLayout()
        self._light_buttons = {}
        for mode, text in (("on", "Вкл"), ("off", "Выкл"), ("auto", "Авто")):
            button = QPushButton(text)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, m=mode: self._set_light(m))
            buttons.addWidget(button)
            self._light_buttons[mode] = button
        panel.addLayout(buttons)

        side = QWidget()
        side.setLayout(panel)
        side.setMinimumWidth(260)
        side.setMaximumWidth(380)
        layout.addWidget(side, stretch=2)
        return root

    # --- события ---

    def _on_reading(self, reading: protocol.Reading) -> None:
        self._reading = reading
        self._reading_at = time.monotonic()
        self._render()

    def _on_status(self, status: protocol.Status) -> None:
        self._status = status
        self._render()

    def _on_connection(self, connected: bool, detail: str) -> None:
        self._connected = connected
        if connected:
            text, color = f"ESP подключена · {detail}", "#238636"
        else:
            text, color = detail, "#da3633"
        self._banner.setText(text)
        self._banner.setStyleSheet(f"background: {color}; color: white;")
        self._render()

    def _on_frame(self, image: QImage) -> None:
        self._pixmap = QPixmap.fromImage(image)
        self._show_frame()

    def _on_camera_failed(self, message: str) -> None:
        self._pixmap = None
        self._camera_view.setPixmap(QPixmap())
        self._camera_view.setText(message)

    def _set_light(self, mode: str) -> None:
        self._link.send(protocol.light_command(mode))
        self._link.send("STATUS")
        self._render()  # кнопки показывают режим из ответа ESP, а не нажатие

    def _tick(self) -> None:
        self._clock.setText(time.strftime("%H:%M"))
        self._render_updated()
        self._render_web()

    def _web_info(self) -> dict:
        return self._web.info() if self._web else {"state": "disabled"}

    def _render_web(self) -> None:
        self._web_row.show_info(self._web_info())

    def _show_web_dialog(self) -> None:
        WebDialog(self._web_info(), self).exec_()

    # --- отрисовка ---

    def _render(self) -> None:
        s = self._settings
        reading = self._reading
        temperature = reading.temperature if reading else None
        humidity = reading.humidity if reading else None

        state = view.level(temperature, s.temp_min, s.temp_max)
        self._temperature.show_value(
            temperature, state, f"{view.LEVEL_TEXT[state]} · норма {s.temp_min:g}–{s.temp_max:g} °C")
        state = view.level(humidity, s.hum_min, s.hum_max)
        self._humidity.show_value(
            humidity, state, f"{view.LEVEL_TEXT[state]} · норма {s.hum_min:g}–{s.hum_max:g} %")
        battery = reading.battery if reading else None
        self._battery.setVisible(battery is not None)
        if battery is not None:
            self._battery.show_value(battery, "ok", "")

        status = self._status
        device_id = status.get("id")
        self._device.setText(
            f"Устройство {device_id} · прошивка {status.get('fw', '?')}" if device_id else "")
        known = self._connected and bool(status.raw)
        wifi = status.get("wifi") if known else None
        self._indicators["wifi"].set(wifi, f"{status.get('rssi')} дБм" if wifi and status.get("rssi") else "")
        self._indicators["mqtt"].set(status.get("mqtt") if known else None,
                                     f"очередь {status.get('queue')}" if known and status.get("queue") else "")
        self._indicators["sd"].set(status.get("sd") if known else None)
        self._indicators["time"].set(status.get("time") if known else None)

        light_on = bool(status.get("light"))
        light_auto = bool(status.get("light_auto"))
        if known:
            mode = "авто, по расписанию" if light_auto else "вручную"
            self._light_state.setText(f"Подсветка: {'включена' if light_on else 'выключена'} ({mode})")
        else:
            self._light_state.setText("Подсветка: нет данных")
        self._light_buttons["auto"].setChecked(known and light_auto)
        self._light_buttons["on"].setChecked(known and not light_auto and light_on)
        self._light_buttons["off"].setChecked(known and not light_auto and not light_on)
        for button in self._light_buttons.values():
            button.setEnabled(self._connected)

        self._render_updated()

    def _render_updated(self) -> None:
        age = None if self._reading_at is None else time.monotonic() - self._reading_at
        stale = view.is_stale(age, self._status.get("interval"))
        text = f"Обновлено: {view.ago(age)}"
        if self._connected and self._status.get("sensor") is False:
            text, stale = "Датчик не отвечает — проверьте провод", True
        elif stale:
            text += " — данные устарели"
        self._updated.setText(text)
        self._updated.setStyleSheet("color: #f0883e;" if stale else "")

    def _show_frame(self) -> None:
        if self._pixmap is None:
            return
        self._camera_view.setPixmap(self._pixmap.scaled(
            self._camera_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._show_frame()

    def _toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def closeEvent(self, event) -> None:
        self._ticker.stop()
        if self._web:
            self._web.stop()
        self._camera.stop()
        self._link.stop()
        event.accept()
