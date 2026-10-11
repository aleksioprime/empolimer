import unittest
from datetime import datetime, timedelta, timezone

from src.models.device import Device, DeviceData
from src.services import monitoring
from src.services.data import bucket_for

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def device(**kwargs) -> Device:
    return Device(name="test", **kwargs)


def reading(temperature=22.0, humidity=50.0) -> DeviceData:
    return DeviceData(timestamp=NOW, temperature=temperature, humidity=humidity)


class EvaluateTest(unittest.TestCase):
    def codes(self, problems):
        return [p.code for p in problems]

    def test_new_device(self):
        online, state, problems = monitoring.evaluate(device(), None, NOW)
        self.assertEqual((online, state, self.codes(problems)), (False, "new", ["new"]))

    def test_ok(self):
        d = device(last_seen=NOW - timedelta(minutes=1), status={"online": True, "sensor": True, "sd": True})
        self.assertEqual(monitoring.evaluate(d, reading(), NOW)[:2], (True, "ok"))

    def test_offline_by_silence_respects_interval(self):
        d = device(last_seen=NOW - timedelta(minutes=6), status={"interval": 60})
        self.assertEqual(monitoring.evaluate(d, reading(), NOW)[1], "offline")
        d = device(last_seen=NOW - timedelta(minutes=6), status={"interval": 300})
        self.assertEqual(monitoring.evaluate(d, reading(), NOW)[1], "ok")

    def test_offline_by_last_will(self):
        d = device(last_seen=NOW, status={"online": False})
        online, state, problems = monitoring.evaluate(d, reading(), NOW)
        self.assertEqual((online, state), (False, "offline"))
        self.assertIn("offline", self.codes(problems))

    def test_out_of_range_uses_device_thresholds(self):
        d = device(last_seen=NOW, status={}, temp_max=35.0)
        _, state, problems = monitoring.evaluate(d, reading(temperature=31, humidity=20), NOW)
        self.assertEqual(state, "warning")
        self.assertEqual(self.codes(problems), ["hum_low"])

    def test_module_problems(self):
        d = device(last_seen=NOW, status={"sensor": False, "sd": False, "time": False, "queue": 3})
        _, state, problems = monitoring.evaluate(d, reading(), NOW)
        self.assertEqual(state, "warning")
        self.assertEqual(self.codes(problems), ["sensor", "sd", "time", "queue"])

    def test_queue_alone_is_not_a_warning(self):
        d = device(last_seen=NOW, status={"queue": 5})
        self.assertEqual(monitoring.evaluate(d, reading(), NOW)[1], "ok")


class BucketTest(unittest.TestCase):
    def test_bucket(self):
        self.assertEqual(bucket_for(NOW - timedelta(hours=6), NOW, 240), 120)
        self.assertEqual(bucket_for(NOW - timedelta(days=1), NOW, 240), 600)
        self.assertEqual(bucket_for(NOW - timedelta(days=30), NOW, 240), 10800)
        self.assertEqual(bucket_for(NOW - timedelta(minutes=30), NOW, 240), 60)


if __name__ == "__main__":
    unittest.main()
