"""Веб-доступ к станции: страница, показания в JSON, видео с камеры и управление подсветкой.

Только стандартная библиотека — на Pi Zero не нужно ничего доустанавливать.

  GET  /               страница станции (station/web/index.html)
  GET  /api/state      показания, состояние ESP и камеры
  GET  /api/ping       проверка, что сервер отвечает
  GET  /stream.mjpg    видео (MJPEG); кадры сжимаются, только пока кто-то смотрит
  GET  /snapshot.jpg   один кадр
  POST /api/light      {"mode": "on" | "off" | "auto"} — если разрешено web_control
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional

from station import protocol
from station.state import StationState

LOG = logging.getLogger(__name__)

PAGE = Path(__file__).resolve().parent / "web" / "index.html"
CLIENT_WINDOW_S = 15      # клиент считается подключённым, если обращался за это время
SELF_CHECK_S = 10
RETRY_BIND_S = 10
SELF_CHECK_HEADER = "X-Station-Self-Check"


def local_addresses(port: int) -> list[str]:
    """Адреса, по которым станцию открывают с других устройств: IP в сети и имя.local."""
    urls = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))  # пакет не отправляется — только выбор интерфейса
            address = probe.getsockname()[0]
        if not address.startswith("127."):
            urls.append(f"http://{address}:{port}")
    except OSError:
        pass
    urls.append(f"http://{socket.gethostname()}.local:{port}")
    return urls


class _Handler(BaseHTTPRequestHandler):
    server: "_Server"
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A002 — журнал запросов не нужен
        pass

    def _track(self) -> None:
        if not self.headers.get(SELF_CHECK_HEADER):
            self.server.station.note_client(self.client_address[0])

    def _send(self, status: int, body: bytes, content_type: str, extra: Optional[dict] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status: int = HTTPStatus.OK) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        self._track()
        path = self.path.split("?", 1)[0]
        web = self.server.station
        if path in ("/", "/index.html"):
            self._send(HTTPStatus.OK, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/state":
            data = web.state.snapshot()
            data["server"] = web.info()
            self._json(data)
        elif path == "/api/ping":
            self._json({"ok": True})
        elif path == "/snapshot.jpg":
            _, jpeg = web.state.jpeg()
            if jpeg is None:
                self._json({"detail": "Камера не работает"}, HTTPStatus.SERVICE_UNAVAILABLE)
            else:
                self._send(HTTPStatus.OK, jpeg, "image/jpeg")
        elif path == "/stream.mjpg":
            self._stream()
        else:
            self._json({"detail": "Не найдено"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        self._track()
        web = self.server.station
        if self.path != "/api/light":
            self._json({"detail": "Не найдено"}, HTTPStatus.NOT_FOUND)
            return
        if not web.state.snapshot()["control"]:
            self._json({"detail": "Управление из браузера выключено (web_control)"}, HTTPStatus.FORBIDDEN)
            return
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 1024)
            mode = json.loads(self.rfile.read(length) or b"{}").get("mode", "")
            command = protocol.light_command(str(mode))
        except (ValueError, AttributeError):
            self._json({"detail": "mode: on, off или auto"}, HTTPStatus.BAD_REQUEST)
            return
        web.send_command(command)
        web.send_command("STATUS")
        self._json({"ok": True, "command": command})

    def _stream(self) -> None:
        web = self.server.station
        period = 1.0 / max(1, web.stream_fps)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        web.viewer(+1)
        last_id = -1
        try:
            while not web.stopping:
                if not web.state.wait_frame(last_id, timeout=2):
                    continue  # камера молчит — держим соединение, браузер покажет последний кадр
                started = time.monotonic()
                last_id, jpeg = web.state.jpeg()
                if jpeg is None:
                    continue
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                self.wfile.write(jpeg + b"\r\n")
                web.note_client(self.client_address[0])
                time.sleep(max(0.0, period - (time.monotonic() - started)))
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        finally:
            web.viewer(-1)
            self.close_connection = True


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    station: "WebServer"


class WebServer:
    """HTTP-сервер в фоновом потоке. Если порт занят — пробует снова, не мешая станции."""

    def __init__(self, state: StationState, port: int, send_command: Callable[[str], None], stream_fps: int = 5):
        self.state = state
        self.port = port
        self.send_command = send_command
        self.stream_fps = stream_fps
        self.stopping = False
        self._lock = threading.Lock()
        self._httpd: Optional[_Server] = None
        self._error = ""
        self._clients: dict[str, float] = {}
        self._viewers = 0
        self._healthy: Optional[bool] = None
        self._checked_at = 0.0
        self._urls: list[str] = []

    # --- запуск ---

    def start(self) -> None:
        if self.port <= 0:
            return
        threading.Thread(target=self._serve, name="web-server", daemon=True).start()
        threading.Thread(target=self._self_check, name="web-check", daemon=True).start()

    def stop(self) -> None:
        self.stopping = True
        if self._httpd:
            self._httpd.shutdown()

    def _serve(self) -> None:
        while not self.stopping:
            try:
                httpd = _Server(("0.0.0.0", self.port), _Handler)
            except OSError as exc:
                with self._lock:
                    self._error = f"порт {self.port} занят" if exc.errno in (48, 98) else str(exc)
                LOG.warning("Веб-сервер не запустился: %s", exc)
                time.sleep(RETRY_BIND_S)
                continue
            httpd.station = self
            with self._lock:
                self._httpd, self._error = httpd, ""
                self._urls = local_addresses(self.port)
            LOG.info("Веб-доступ: %s", ", ".join(self._urls))
            httpd.serve_forever(poll_interval=0.5)
            httpd.server_close()
            return

    def _self_check(self) -> None:
        """Раз в SELF_CHECK_S секунд запрашивает /api/ping у самого себя — так видно, что сервер отвечает.
        Пока сервер не ответил ни разу (только запускается), проверка повторяется каждую секунду."""
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/ping", headers={SELF_CHECK_HEADER: "1"})
        while not self.stopping:
            if self._httpd is None:  # сервер ещё не занял порт — проверять рано
                time.sleep(0.2)
                continue
            try:
                with urllib.request.urlopen(request, timeout=3) as response:
                    healthy = response.status == 200
            except OSError:
                healthy = False
            with self._lock:
                self._healthy, self._checked_at = healthy, time.monotonic()
                if healthy:
                    self._urls = local_addresses(self.port)  # адрес мог смениться после переподключения Wi-Fi
            time.sleep(SELF_CHECK_S if healthy else 1)

    # --- учёт клиентов ---

    def note_client(self, address: str) -> None:
        with self._lock:
            self._clients[address] = time.monotonic()

    def viewer(self, delta: int) -> None:
        with self._lock:
            self._viewers += delta

    def info(self) -> dict:
        """Состояние сервера для экрана станции и страницы."""
        now = time.monotonic()
        with self._lock:
            self._clients = {ip: t for ip, t in self._clients.items() if now - t < CLIENT_WINDOW_S}
            if self.port <= 0:
                state = "disabled"
            elif self._error:
                state = "error"
            elif self._healthy is None:
                state = "starting"
            else:
                state = "ok" if self._healthy else "error"
            return {
                "state": state,
                "error": self._error or ("сервер не отвечает" if self._healthy is False else ""),
                "port": self.port,
                "urls": list(self._urls),
                "clients": len(self._clients),
                "viewers": self._viewers,
            }
