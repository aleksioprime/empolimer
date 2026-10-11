import tempfile
import unittest
from pathlib import Path

from station import config


class ConfigTest(unittest.TestCase):
    def write(self, text: str) -> Path:
        path = Path(tempfile.mkdtemp()) / "station.conf"
        path.write_text(text, encoding="utf-8")
        return path

    def test_defaults_without_file(self):
        settings = config.load(["--config", "/nonexistent/station.conf"])
        self.assertEqual(settings.port, "auto")
        self.assertTrue(settings.fullscreen)

    def test_file_values_and_bad_lines(self):
        path = self.write(
            "port = /dev/ttyACM0  # комментарий\n"
            "fps = много\n"
            "fullscreen = no\n"
            "temp_max = 30.5\n"
            "unknown = 1\n"
            "просто строка\n"
        )
        settings = config.load(["--config", str(path)])
        self.assertEqual(settings.port, "/dev/ttyACM0")
        self.assertEqual(settings.fps, 10)
        self.assertFalse(settings.fullscreen)
        self.assertEqual(settings.temp_max, 30.5)

    def test_arguments_override_file(self):
        path = self.write("port = /dev/ttyACM0\ncamera = usb\n")
        settings = config.load(["--config", str(path), "--port", "/dev/ttyUSB1", "--window"])
        self.assertEqual(settings.port, "/dev/ttyUSB1")
        self.assertEqual(settings.camera, "usb")
        self.assertFalse(settings.fullscreen)

    def test_frame_size(self):
        self.assertEqual(config.Settings(camera_size="320x240").frame_size, (320, 240))
        self.assertEqual(config.Settings(camera_size="large").frame_size, (640, 480))


if __name__ == "__main__":
    unittest.main()
