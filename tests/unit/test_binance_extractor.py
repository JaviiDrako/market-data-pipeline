from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.extraction.binance_extractor import (
    BINANCE_KLINES_MAX_LIMIT,
    BinanceExtractor,
)


def _fake_kline(open_ms: int) -> list:
    return [
        open_ms,
        "100",
        "110",
        "90",
        "105",
        "50",
        open_ms + 59_999,
        "5000",
        10,
        "20",
        "2000",
        "0",
    ]


class TestBinanceExtractor(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = MagicMock()
        self.settings.get_symbols.return_value = ["BTCUSDT", "ETHUSDT"]
        self.settings.get_history_interval.return_value = "1m"
        self.settings.get_history_days.return_value = 365
        self.client = MagicMock()
        self.extractor = BinanceExtractor(self.settings, self.client)

    def test_extract_klines_without_dates_matches_legacy_latest(self) -> None:
        """Without dates and limit=1, behaviour equals previous extract_latest_klines."""
        self.client.get_historical_klines.side_effect = [
            [_fake_kline(1_000)],
            [_fake_kline(2_000)],
        ]

        result = self.extractor.extract_klines(limit=1)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["symbol"], "BTCUSDT")
        self.assertEqual(result[0]["open_time"], 1_000)
        self.assertEqual(result[1]["symbol"], "ETHUSDT")

        self.assertEqual(self.client.get_historical_klines.call_count, 2)
        for call in self.client.get_historical_klines.call_args_list:
            kwargs = call.kwargs
            self.assertEqual(kwargs["limit"], 1)
            self.assertIsNone(kwargs["start_time"])
            self.assertIsNone(kwargs["end_time"])
            self.assertEqual(kwargs["interval"], "1m")

    def test_extract_latest_klines_alias(self) -> None:
        self.client.get_historical_klines.return_value = [_fake_kline(1_000)]
        via_alias = self.extractor.extract_latest_klines()
        self.assertEqual(len(via_alias), 2)

    def test_extract_klines_with_dates(self) -> None:
        self.client.get_historical_klines.return_value = [
            _fake_kline(1_700_000_000_000),
            _fake_kline(1_700_000_060_000),
        ]

        start = 1_700_000_000_000
        end = 1_700_000_120_000
        result = self.extractor.extract_klines(
            start_time=start,
            end_time=end,
            limit=1000,
            symbols=["BTCUSDT"],
        )

        self.assertEqual(len(result), 2)
        self.client.get_historical_klines.assert_called_once_with(
            symbol="BTCUSDT",
            interval="1m",
            start_time=start,
            end_time=end,
            limit=1000,
        )

    def test_extract_klines_multiple_blocks_via_caller_pagination(self) -> None:
        """Caller paginates: full block then remainder."""
        block1 = [_fake_kline(i * 60_000) for i in range(BINANCE_KLINES_MAX_LIMIT)]
        block2 = [
            _fake_kline((BINANCE_KLINES_MAX_LIMIT + i) * 60_000) for i in range(50)
        ]
        self.client.get_historical_klines.side_effect = [block1, block2]

        all_rows: list = []
        current = 0
        end = 10**15
        for _ in range(2):
            batch = self.extractor.extract_klines(
                start_time=current,
                end_time=end,
                limit=BINANCE_KLINES_MAX_LIMIT,
                symbols=["BTCUSDT"],
            )
            all_rows.extend(batch)
            if not batch:
                break
            current = max(int(r["open_time"]) for r in batch) + 1
            if len(batch) < BINANCE_KLINES_MAX_LIMIT:
                break

        self.assertEqual(len(all_rows), BINANCE_KLINES_MAX_LIMIT + 50)
        self.assertEqual(self.client.get_historical_klines.call_count, 2)

    def test_extract_klines_rejects_limit_above_binance_max(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.extractor.extract_klines(limit=BINANCE_KLINES_MAX_LIMIT + 1)
        self.assertIn("cannot exceed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
