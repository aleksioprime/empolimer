import unittest

from station import protocol


class ParseLineTest(unittest.TestCase):
    def test_data(self):
        message = protocol.parse_line('{"type":"data","ts":1760000000,"temp":23.5,"hum":41.0}')
        self.assertEqual(message, protocol.Reading(23.5, 41.0, None, 1760000000))

    def test_data_without_time_and_with_battery(self):
        message = protocol.parse_line('{"type":"data","temp":20,"hum":50,"bat":3.91}')
        self.assertEqual(message, protocol.Reading(20.0, 50.0, 3.91, None))

    def test_data_without_values_is_ignored(self):
        self.assertIsNone(protocol.parse_line('{"type":"data","temp":null,"hum":50}'))

    def test_status(self):
        message = protocol.parse_line('{"type":"status","wifi":true,"sd":false}')
        self.assertIsInstance(message, protocol.Status)
        self.assertTrue(message.get("wifi"))
        self.assertFalse(message.get("sd"))

    def test_ack(self):
        message = protocol.parse_line('{"type":"ack","cmd":"LIGHT 300","ok":false,"error":"яркость"}')
        self.assertEqual(message, protocol.Ack("LIGHT 300", False, "яркость"))

    def test_log(self):
        self.assertEqual(protocol.parse_line("# Wi-Fi: подключено"), protocol.Log("Wi-Fi: подключено"))

    def test_garbage(self):
        for line in ("", "   ", "\x00\xff rl", "{broken", "[1,2]", '{"type":"unknown"}'):
            self.assertIsNone(protocol.parse_line(line), line)


class CommandsTest(unittest.TestCase):
    def test_light(self):
        self.assertEqual(protocol.light_command("on"), "LIGHT ON")
        self.assertEqual(protocol.light_command("ON", 300), "LIGHT ON 255")
        self.assertEqual(protocol.light_command("off"), "LIGHT OFF")
        self.assertEqual(protocol.light_command("auto"), "LIGHT AUTO")
        with self.assertRaises(ValueError):
            protocol.light_command("blink")

    def test_time(self):
        self.assertEqual(protocol.time_command(1760000000.7), "TIME 1760000000")


if __name__ == "__main__":
    unittest.main()
