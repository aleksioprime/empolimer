import unittest
from datetime import datetime, timedelta, timezone

from src.utils.parse import parse_reading, parse_timestamp, parse_topic, Topic

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


class TopicTest(unittest.TestCase):
    def test_topics(self):
        self.assertEqual(parse_topic("empolimer/greenhouse-1/data"), Topic("greenhouse-1", "data"))
        self.assertEqual(parse_topic("empolimer/lab_2/status"), Topic("lab_2", "status"))
        self.assertEqual(parse_topic("devices/demo/air"), Topic("demo", "data"))  # старые прошивки

    def test_bad_topics(self):
        for topic in ("empolimer/x/cmd", "empolimer/x", "empolimer/bad id/data", "devices/x/data", "a/b/c/d"):
            self.assertIsNone(parse_topic(topic), topic)


class TimestampTest(unittest.TestCase):
    def test_unix(self):
        ts = int((NOW - timedelta(hours=2)).timestamp())
        self.assertEqual(parse_timestamp({"ts": ts}, NOW), NOW - timedelta(hours=2))

    def test_legacy_iso(self):
        self.assertEqual(
            parse_timestamp({"datetime": "2026-10-11T14:30:00+03:00"}, NOW),
            datetime(2026, 10, 11, 11, 30, tzinfo=timezone.utc),
        )

    def test_missing_or_wrong_clock_uses_now(self):
        for payload in ({}, {"ts": 0}, {"ts": True}, {"datetime": "none"},
                        {"ts": int((NOW + timedelta(hours=1)).timestamp())},
                        {"ts": int((NOW - timedelta(days=400)).timestamp())}):
            self.assertEqual(parse_timestamp(payload, NOW), NOW, payload)


class ReadingTest(unittest.TestCase):
    def test_values(self):
        reading = parse_reading({"ts": int(NOW.timestamp()), "temp": 23.5, "hum": "41", "bat": 3.9}, NOW)
        self.assertEqual((reading.temperature, reading.humidity, reading.battery), (23.5, 41.0, 3.9))

    def test_implausible_values_dropped(self):
        reading = parse_reading({"temp": 150, "hum": 50}, NOW)
        self.assertIsNone(reading.temperature)
        self.assertEqual(reading.humidity, 50)
        self.assertIsNone(parse_reading({"temp": "nan", "hum": -5}, NOW))
        self.assertIsNone(parse_reading({"bat": 3.9}, NOW))


if __name__ == "__main__":
    unittest.main()
