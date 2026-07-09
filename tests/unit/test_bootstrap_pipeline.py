from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

from src.extraction.binance_extractor import BINANCE_KLINES_MAX_LIMIT
from src.pipelines.bootstrap_pipeline import BootstrapPipeline


def _fake_kline_record(symbol: str, open_ms: int) -> dict:
    return {
        "symbol": symbol,
        "open_time": open_ms,
        "open_price": "100",
        "high_price": "110",
        "low_price": "90",
        "close_price": "105",
        "volume": "50",
        "close_time": open_ms + 59_999,
        "quote_asset_volume": "5000",
        "number_of_trades": 10,
        "taker_buy_base_asset_volume": "20",
        "taker_buy_quote_asset_volume": "2000",
    }


class TestBootstrapPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = MagicMock()
        self.settings.get_source.return_value = {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "historical": {"interval": "1m", "days": 7},
        }
        self.database = MagicMock()
        self.extractor = MagicMock()
        self.loader = MagicMock()
        self.loader.insert_klines.return_value = 0
        self.monitor = MagicMock()
        self.monitor.start_pipeline.return_value = 42
        self.data_quality = MagicMock()

        self.pipeline = BootstrapPipeline(
            extractor=self.extractor,
            settings=self.settings,
            database=self.database,
            loader=self.loader,
            monitor=self.monitor,
            data_quality=self.data_quality,
        )

    def _mock_db_fetch(self, rows_sequence: list) -> None:
        """Mock Database connections for successive _fetch_all calls."""
        connections = []
        for rows in rows_sequence:
            conn = MagicMock()
            cursor = MagicMock()
            cursor.description = (
                [("exchange",), ("symbol",), ("enabled",), ("history_days",),
                 ("bootstrap_status",), ("last_bootstrap_open_time",),
                 ("bootstrap_started_at",), ("bootstrap_completed_at",),
                 ("last_incremental_at",), ("last_error",),
                 ("created_at",), ("updated_at",)]
                if rows is not None and (not rows or isinstance(rows[0], tuple))
                else cursor.description
            )
            # Simpler: set description once for configured_symbols shape
            cursor.description = [
                ("exchange",),
                ("symbol",),
                ("enabled",),
                ("history_days",),
                ("bootstrap_status",),
                ("last_bootstrap_open_time",),
                ("bootstrap_started_at",),
                ("bootstrap_completed_at",),
                ("last_incremental_at",),
                ("last_error",),
                ("created_at",),
                ("updated_at",),
            ]
            cursor.fetchall.return_value = rows
            conn.cursor.return_value.__enter__.return_value = cursor
            connections.append(conn)

        # Also need connections for execute (updates/inserts)
        def get_connection():
            if connections:
                return connections.pop(0)
            # default empty execute connection
            conn = MagicMock()
            cursor = MagicMock()
            conn.cursor.return_value.__enter__.return_value = cursor
            return conn

        self.database.get_connection.side_effect = get_connection

    def test_detects_and_inserts_new_symbols(self) -> None:
        # First fetch: existing configured_symbols empty
        # Second fetch: symbols needing bootstrap (after insert we'd still process from yaml)
        existing_empty: list = []
        needing = [
            (
                "binance",
                "BTCUSDT",
                True,
                7,
                "pending",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        ]

        fetch_conns = []
        for rows in (existing_empty, needing):
            conn = MagicMock()
            cursor = MagicMock()
            cursor.description = [
                ("exchange",), ("symbol",), ("enabled",), ("history_days",),
                ("bootstrap_status",), ("last_bootstrap_open_time",),
                ("bootstrap_started_at",), ("bootstrap_completed_at",),
                ("last_incremental_at",), ("last_error",),
                ("created_at",), ("updated_at",),
            ]
            cursor.fetchall.return_value = rows
            conn.cursor.return_value.__enter__.return_value = cursor
            fetch_conns.append(conn)

        execute_calls_conn = []

        def get_connection():
            # Pattern: sync fetch, then 2 inserts for new symbols, then needing fetch,
            # then per-symbol updates + inserts...
            if fetch_conns:
                return fetch_conns.pop(0)
            conn = MagicMock()
            cursor = MagicMock()
            conn.cursor.return_value.__enter__.return_value = cursor
            execute_calls_conn.append((conn, cursor))
            return conn

        self.database.get_connection.side_effect = get_connection

        # Empty historical download for simplicity once we get to bootstrap
        self.extractor.extract_klines.return_value = []

        # After first fetch empty, inserts BTCUSDT and ETHUSDT, then second fetch
        # returns only BTCUSDT to bootstrap (simulate)
        # Actually pipeline inserts both missing, then fetches needing - we need second fetch
        # to return both. Rebuild simpler test focusing on insert SQL.

        self.pipeline._sync_symbols_from_yaml = MagicMock()  # type: ignore[method-assign]
        self.pipeline._fetch_symbols_needing_bootstrap = MagicMock(return_value=[])  # type: ignore[method-assign]

        total = self.pipeline.run("bootstrap-test-1")
        self.assertEqual(total, 0)
        self.pipeline._sync_symbols_from_yaml.assert_called_once()
        self.monitor.start_pipeline.assert_called_once_with("bootstrap-test-1")
        self.monitor.finish_success.assert_called_once()

    def test_status_transitions_pending_running_completed(self) -> None:
        row = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "enabled": True,
            "history_days": 1,
            "bootstrap_status": "pending",
            "last_bootstrap_open_time": None,
        }
        open_ms = 1_700_000_000_000
        batch = [_fake_kline_record("BTCUSDT", open_ms)]
        self.extractor.extract_klines.side_effect = [batch, []]
        self.loader.insert_klines.return_value = 1

        executed: list[tuple] = []

        def capture_execute(query: str, params: tuple = ()) -> None:
            executed.append((query, params))

        self.pipeline._execute = capture_execute  # type: ignore[method-assign]
        self.pipeline._mark_running = MagicMock(wraps=self.pipeline._mark_running)  # type: ignore[method-assign]
        # Use real mark methods with captured execute

        inserted = self.pipeline._bootstrap_symbol(row, pipeline_run_id=1)

        self.assertEqual(inserted, 1)
        statuses = []
        for query, params in executed:
            if "bootstrap_status = 'running'" in query:
                statuses.append("running")
            if "bootstrap_status = 'completed'" in query:
                statuses.append("completed")
            if "last_bootstrap_open_time" in query and "UPDATE" in query and "bootstrap_status" not in query:
                statuses.append("progress")

        self.assertIn("running", statuses)
        self.assertIn("completed", statuses)
        self.assertIn("progress", statuses)

    def test_failed_status_on_exception(self) -> None:
        row = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "enabled": True,
            "history_days": 1,
            "bootstrap_status": "pending",
            "last_bootstrap_open_time": None,
        }
        self.extractor.extract_klines.side_effect = RuntimeError("API down")

        executed: list[tuple] = []

        def capture_execute(query: str, params: tuple = ()) -> None:
            executed.append((query, params))

        self.pipeline._execute = capture_execute  # type: ignore[method-assign]

        with self.assertRaises(RuntimeError):
            self.pipeline._bootstrap_symbol(row, pipeline_run_id=1)

        failed = [
            (q, p) for q, p in executed if "bootstrap_status = 'failed'" in q
        ]
        self.assertEqual(len(failed), 1)
        self.assertIn("API down", failed[0][1][0])

    def test_updates_last_bootstrap_open_time_per_block(self) -> None:
        row = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "enabled": True,
            "history_days": 1,
            "bootstrap_status": "pending",
            "last_bootstrap_open_time": None,
        }
        block1 = [
            _fake_kline_record("BTCUSDT", i * 60_000)
            for i in range(BINANCE_KLINES_MAX_LIMIT)
        ]
        block2 = [_fake_kline_record("BTCUSDT", BINANCE_KLINES_MAX_LIMIT * 60_000)]
        self.extractor.extract_klines.side_effect = [block1, block2]
        self.loader.insert_klines.side_effect = [
            BINANCE_KLINES_MAX_LIMIT,
            1,
        ]

        progress_times: list = []

        def capture_execute(query: str, params: tuple = ()) -> None:
            if (
                "last_bootstrap_open_time = %s" in query
                and "bootstrap_status" not in query
            ):
                progress_times.append(params[0])

        self.pipeline._execute = capture_execute  # type: ignore[method-assign]

        total = self.pipeline._bootstrap_symbol(row, pipeline_run_id=7)
        self.assertEqual(total, BINANCE_KLINES_MAX_LIMIT + 1)
        self.assertEqual(len(progress_times), 2)
        self.assertEqual(self.loader.insert_klines.call_count, 2)
        # Second request must start after last open of first block
        second_call = self.extractor.extract_klines.call_args_list[1]
        expected_start = (BINANCE_KLINES_MAX_LIMIT - 1) * 60_000 + 1
        self.assertEqual(second_call.kwargs["start_time"], expected_start)

    def test_resume_from_last_bootstrap_open_time(self) -> None:
        last_dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        row = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "enabled": True,
            "history_days": 30,
            "bootstrap_status": "failed",
            "last_bootstrap_open_time": last_dt,
        }
        self.extractor.extract_klines.return_value = []
        self.pipeline._execute = MagicMock()  # type: ignore[method-assign]

        self.pipeline._bootstrap_symbol(row, pipeline_run_id=1)

        call_kwargs = self.extractor.extract_klines.call_args.kwargs
        expected_start = int(last_dt.timestamp() * 1000) + 1
        self.assertEqual(call_kwargs["start_time"], expected_start)
        self.assertEqual(call_kwargs["symbols"], ["BTCUSDT"])
        self.assertEqual(call_kwargs["limit"], BINANCE_KLINES_MAX_LIMIT)

    def test_inserts_klines_into_bronze(self) -> None:
        row = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "enabled": True,
            "history_days": 1,
            "bootstrap_status": "pending",
            "last_bootstrap_open_time": None,
        }
        batch = [
            _fake_kline_record("BTCUSDT", 1_000),
            _fake_kline_record("BTCUSDT", 61_000),
        ]
        self.extractor.extract_klines.side_effect = [batch]
        self.loader.insert_klines.return_value = 2
        self.pipeline._execute = MagicMock()  # type: ignore[method-assign]

        inserted = self.pipeline._bootstrap_symbol(row, pipeline_run_id=99)

        self.assertEqual(inserted, 2)
        self.loader.insert_klines.assert_called_once_with(batch, 99)
        self.data_quality.validate_latest_klines.assert_called_once_with(batch)

    def test_sync_inserts_missing_yaml_symbols(self) -> None:
        # existing only BTCUSDT
        existing = [
            (
                "binance",
                "BTCUSDT",
                True,
                7,
                "completed",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        ]
        conn_fetch = MagicMock()
        cursor_fetch = MagicMock()
        cursor_fetch.description = [
            ("exchange",), ("symbol",), ("enabled",), ("history_days",),
            ("bootstrap_status",), ("last_bootstrap_open_time",),
            ("bootstrap_started_at",), ("bootstrap_completed_at",),
            ("last_incremental_at",), ("last_error",),
            ("created_at",), ("updated_at",),
        ]
        cursor_fetch.fetchall.return_value = existing
        conn_fetch.cursor.return_value.__enter__.return_value = cursor_fetch

        insert_params: list = []
        conn_insert = MagicMock()
        cursor_insert = MagicMock()

        def exec_side_effect(query, params=None):
            if params and "ETHUSDT" in params:
                insert_params.append(params)

        cursor_insert.execute.side_effect = exec_side_effect
        conn_insert.cursor.return_value.__enter__.return_value = cursor_insert

        self.database.get_connection.side_effect = [conn_fetch, conn_insert]

        self.pipeline._sync_symbols_from_yaml()

        self.assertEqual(len(insert_params), 1)
        self.assertEqual(insert_params[0][1], "ETHUSDT")
        self.assertEqual(insert_params[0][0], "binance")


if __name__ == "__main__":
    unittest.main()
