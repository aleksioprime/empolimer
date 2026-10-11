import unittest

from station import view


class ViewTest(unittest.TestCase):
    def test_level(self):
        self.assertEqual(view.level(None, 18, 28), "unknown")
        self.assertEqual(view.level(17.9, 18, 28), "low")
        self.assertEqual(view.level(18, 18, 28), "ok")
        self.assertEqual(view.level(28.1, 18, 28), "high")

    def test_ago(self):
        self.assertEqual(view.ago(None), "измерений ещё не было")
        self.assertEqual(view.ago(2), "только что")
        self.assertEqual(view.ago(42), "42 с назад")
        self.assertEqual(view.ago(185), "3 мин назад")
        self.assertEqual(view.ago(3 * 3600 + 120), "3 ч 2 мин назад")

    def test_stale(self):
        self.assertFalse(view.is_stale(None, 60))
        self.assertFalse(view.is_stale(170, 60))
        self.assertTrue(view.is_stale(181, 60))
        self.assertTrue(view.is_stale(121, 5))  # не меньше двух минут


if __name__ == "__main__":
    unittest.main()
