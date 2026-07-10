from __future__ import annotations

import unittest

from src.common.interval_cron import interval_to_cron, supported_intervals


class TestIntervalToCron(unittest.TestCase):
    def test_supported_mappings(self) -> None:
        expected = {
            "1m": "* * * * *",
            "5m": "*/5 * * * *",
            "15m": "*/15 * * * *",
            "30m": "*/30 * * * *",
            "1h": "0 * * * *",
            "1d": "0 0 * * *",
        }
        for interval, cron in expected.items():
            with self.subTest(interval=interval):
                self.assertEqual(interval_to_cron(interval), cron)

    def test_case_and_whitespace(self) -> None:
        self.assertEqual(interval_to_cron(" 1H "), "0 * * * *")

    def test_unsupported_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            interval_to_cron("2h")
        self.assertIn("Unsupported interval", str(ctx.exception))

    def test_supported_intervals_list(self) -> None:
        self.assertIn("1m", supported_intervals())
        self.assertIn("1d", supported_intervals())


if __name__ == "__main__":
    unittest.main()
