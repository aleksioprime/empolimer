import json
import socket
import threading
import time
import unittest
import urllib.error
import urllib.request

from station import protocol
from station.config import Settings
from station.state import StationState
from station.web import WebServer


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class WebServerTest(unittest.TestCase):
    def setUp(self):
        self.commands = []
        self.settings = Settings(temp_max=28)
        self.state = StationState(self.settings, encode=lambda frame: b"\xff\xd8" + frame + b"\xff\xd9")
        self.port = free_port()
        self.web = WebServer(self.state, self.port, self.commands.append, stream_fps=20)
        self.web.start()
        self.url = f"http://127.0.0.1:{self.port}"
        for _ in range(50):
            try:
                urllib.request.urlopen(self.url + "/api/ping", timeout=1)
                break
            except OSError:
                time.sleep(0.05)

    def tearDown(self):
        self.web.stop()

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=3) as response:
            return response.status, response.headers.get("Content-Type"), response.read()

    def post(self, path, body):
        request = urllib.request.Request(self.url + path, data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_page(self):
        status, kind, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", kind)
        self.assertIn("Станция ЕмПолимер".encode(), body)

    def test_state(self):
        self.state.set_connection(True, "/dev/ttyUSB0")
        self.state.set_status(protocol.Status({"type": "status", "id": "greenhouse-1", "light": True}))
        self.state.set_reading(protocol.Reading(29.5, 50.0))
        _, _, body = self.get("/api/state")
        data = json.loads(body)
        self.assertTrue(data["esp"]["connected"])
        self.assertEqual(data["reading"]["temperature"], 29.5)
        self.assertEqual(data["levels"], {"temperature": "high", "humidity": "ok"})
        self.assertEqual(data["status"]["id"], "greenhouse-1")
        self.assertEqual(data["server"]["port"], self.port)

    def test_disconnect_clears_status(self):
        self.state.set_status(protocol.Status({"wifi": True}))
        self.state.set_connection(False, "ESP не найдена")
        self.assertEqual(self.state.snapshot()["status"], {})

    def test_snapshot_and_stream(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.get("/snapshot.jpg")
        self.assertEqual(error.exception.code, 503)

        self.state.set_frame(b"frame1")
        status, kind, body = self.get("/snapshot.jpg")
        self.assertEqual((status, kind, body), (200, "image/jpeg", b"\xff\xd8frame1\xff\xd9"))

        threading.Timer(0.3, lambda: self.state.set_frame(b"frame2")).start()
        with urllib.request.urlopen(self.url + "/stream.mjpg", timeout=3) as response:
            self.assertIn("multipart/x-mixed-replace", response.headers["Content-Type"])
            chunk = response.read1(4096) if hasattr(response, "read1") else response.read(200)
            while b"\xff\xd9" not in chunk:
                chunk += response.read1(4096)
            self.assertIn(b"--frame", chunk)
            self.assertEqual(self.web.info()["viewers"], 1)

    def test_light_control(self):
        self.assertEqual(self.post("/api/light", {"mode": "on"})[0], 200)
        self.assertEqual(self.commands, ["LIGHT ON", "STATUS"])
        self.assertEqual(self.post("/api/light", {"mode": "blink"})[0], 400)

    def test_light_control_disabled(self):
        self.settings.web_control = False
        status, data = self.post("/api/light", {"mode": "off"})
        self.assertEqual(status, 403)
        self.assertEqual(self.commands, [])

    def test_info_counts_clients_and_reports_health(self):
        self.get("/api/state")
        info = self.web.info()
        self.assertEqual(info["clients"], 1)
        for _ in range(40):  # самопроверка запускается сразу после старта
            if self.web.info()["state"] == "ok":
                break
            time.sleep(0.05)
        self.assertEqual(self.web.info()["state"], "ok")
        self.assertTrue(info["urls"])

    def test_port_busy_is_reported(self):
        busy = WebServer(self.state, self.port, self.commands.append)  # порт уже занят сервером из setUp
        busy.start()
        for _ in range(40):
            if busy.info()["error"]:
                break
            time.sleep(0.05)
        info = busy.info()
        busy.stop()
        self.assertEqual(info["state"], "error")
        self.assertIn("занят", info["error"])

    def test_disabled(self):
        web = WebServer(self.state, 0, self.commands.append)
        web.start()
        self.assertEqual(web.info()["state"], "disabled")


if __name__ == "__main__":
    unittest.main()
