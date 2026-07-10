from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.quality.maintenance_checks import (
    BRONZE_FRESHNESS_MAX_AGE,
    MaintenanceCheckError,
    check_bronze_freshness,
    check_configured_symbols,
    check_gold_consistency,
    check_gold_tables,
    check_pipeline_runs,
)


class TestMaintenanceChecks(unittest.TestCase):
    def test_pipeline_runs_success(self) -> None:
        db = MagicMock()
        with patch(
            "src.quality.maintenance_checks._fetch_one",
            return_value=(1, "success", "run-1", datetime.now(timezone.utc)),
        ):
            result = check_pipeline_runs(db)
        self.assertIn("ok", result)

    def test_pipeline_runs_failed_status(self) -> None:
        db = MagicMock()
        with patch(
            "src.quality.maintenance_checks._fetch_one",
            return_value=(2, "failed", "run-2", datetime.now(timezone.utc)),
        ):
            with self.assertRaises(MaintenanceCheckError):
                check_pipeline_runs(db)

    def test_configured_symbols_ok(self) -> None:
        db = MagicMock()
        with patch(
            "src.quality.maintenance_checks._fetch_all",
            return_value=[
                ("BTCUSDT", True, "completed"),
                ("ETHUSDT", True, "pending"),
            ],
        ):
            result = check_configured_symbols(db)
        self.assertIn("ok", result)

    def test_configured_symbols_failed(self) -> None:
        db = MagicMock()
        with patch(
            "src.quality.maintenance_checks._fetch_all",
            return_value=[("BTCUSDT", True, "failed")],
        ):
            with self.assertRaises(MaintenanceCheckError):
                check_configured_symbols(db)

    def test_bronze_freshness_ok(self) -> None:
        db = MagicMock()
        recent = datetime.now(timezone.utc) - timedelta(minutes=10)
        with patch(
            "src.quality.maintenance_checks._fetch_one",
            return_value=(recent,),
        ):
            result = check_bronze_freshness(db)
        self.assertIn("ok", result)

    def test_bronze_freshness_stale(self) -> None:
        db = MagicMock()
        stale = datetime.now(timezone.utc) - BRONZE_FRESHNESS_MAX_AGE - timedelta(minutes=1)
        with patch(
            "src.quality.maintenance_checks._fetch_one",
            return_value=(stale,),
        ):
            with self.assertRaises(MaintenanceCheckError):
                check_bronze_freshness(db)

    def test_gold_tables_empty(self) -> None:
        db = MagicMock()
        with patch(
            "src.quality.maintenance_checks._fetch_one",
            return_value=(0,),
        ):
            with self.assertRaises(MaintenanceCheckError):
                check_gold_tables(db)

    def test_gold_consistency_mismatch(self) -> None:
        db = MagicMock()
        # Four sequential COUNT(*) calls with different values
        with patch(
            "src.quality.maintenance_checks._fetch_one",
            side_effect=[(10,), (10,), (9,), (10,)],
        ):
            with self.assertRaises(MaintenanceCheckError):
                check_gold_consistency(db)

    def test_gold_consistency_ok(self) -> None:
        db = MagicMock()
        with patch(
            "src.quality.maintenance_checks._fetch_one",
            side_effect=[(10,), (10,), (10,), (10,)],
        ):
            result = check_gold_consistency(db)
        self.assertEqual(result, "ok:count=10")


if __name__ == "__main__":
    unittest.main()
