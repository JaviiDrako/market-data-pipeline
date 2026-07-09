"""
Integration test: Bootstrap Pipeline only (no dbt / full E2E).

Assumes PostgreSQL warehouse is up (docker compose).
Uses the same production configuration as BootstrapPipeline (Settings / config.yaml).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.common.database import Database
from src.config.settings import Settings
from src.pipelines.bootstrap_pipeline import EXCHANGE, BootstrapPipeline


def _get_connection():
    return Database().get_connection()


def _execute(query: str, params: tuple = ()) -> None:
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _fetch_all(query: str, params: tuple = ()) -> list[tuple]:
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()


def _fetch_one(query: str, params: tuple = ()):
    rows = _fetch_all(query, params)
    return rows[0] if rows else None


def _clean_bootstrap_tables() -> None:
    """Isolate bootstrap test data without dropping schemas."""
    _execute(
        """
        TRUNCATE TABLE
            bronze.binance_klines,
            bronze.binance_price,
            bronze.binance_ticker_24h,
            bronze.pipeline_runs,
            bronze.configured_symbols
        RESTART IDENTITY CASCADE
        """
    )


def _count_klines() -> int:
    return int(_fetch_one("SELECT COUNT(*) FROM bronze.binance_klines")[0])


def _count_klines_by_symbol() -> dict[str, int]:
    rows = _fetch_all(
        "SELECT symbol, COUNT(*) FROM bronze.binance_klines GROUP BY symbol ORDER BY symbol"
    )
    return {r[0]: int(r[1]) for r in rows}


settings = Settings()
configured_symbols = settings.get_symbols(EXCHANGE)
history_days = settings.get_history_days(EXCHANGE)
history_interval = settings.get_history_interval(EXCHANGE)
expected_rows = history_days * 24 * 60 * len(configured_symbols)

print("=" * 80)
print("BOOTSTRAP INTEGRATION TEST")
print("=" * 80)
print(f"Settings symbols  : {configured_symbols}")
print(f"Settings days     : {history_days}")
print(f"Settings interval : {history_interval}")
print(f"Expected klines   : {expected_rows}")

print("\n[1] Cleaning bronze tables for isolated bootstrap run...")
_clean_bootstrap_tables()
assert _count_klines() == 0
assert _fetch_one("SELECT COUNT(*) FROM bronze.configured_symbols")[0] == 0
print("    Tables truncated.")

print(f"\n[2] First Bootstrap run (history_days={history_days} from Settings)...")
pipeline = BootstrapPipeline()
run_id_1 = "bootstrap_it_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
rows_1 = pipeline.run(run_id_1)
print(f"    rows_submitted={rows_1}")

print("\n[3] Verify configured_symbols populated and statuses...")
symbols = _fetch_all(
    """
    SELECT symbol, enabled, history_days, bootstrap_status,
           last_bootstrap_open_time IS NOT NULL AS has_progress,
           last_error
    FROM bronze.configured_symbols
    ORDER BY symbol
    """
)
print("    configured_symbols:")
for row in symbols:
    print(f"      {row}")

db_symbol_names = [row[0] for row in symbols]
assert db_symbol_names == sorted(configured_symbols), (
    f"configured_symbols mismatch: db={db_symbol_names} settings={sorted(configured_symbols)}"
)
assert len(symbols) == len(configured_symbols)

for symbol, enabled, history_days_db, status, has_progress, last_error in symbols:
    assert enabled is True
    assert int(history_days_db) == history_days
    assert status == "completed", f"{symbol} expected completed, got {status}"
    assert has_progress is True, f"{symbol} missing last_bootstrap_open_time"
    assert last_error is None

print("\n[4] Verify klines inserted...")
total_klines = _count_klines()
by_symbol = _count_klines_by_symbol()
print(f"    total klines={total_klines} (expected {expected_rows})")
for sym, cnt in by_symbol.items():
    print(f"      {sym}: {cnt}")

assert total_klines == expected_rows, (
    f"expected exactly {expected_rows} klines "
    f"({history_days}d × 24 × 60 × {len(configured_symbols)} symbols), got {total_klines}"
)
for sym in configured_symbols:
    per_symbol_expected = history_days * 24 * 60
    assert by_symbol.get(sym) == per_symbol_expected, (
        f"{sym}: expected {per_symbol_expected} klines, got {by_symbol.get(sym)}"
    )

ranges = _fetch_all(
    """
    SELECT symbol, MIN(open_time), MAX(open_time), COUNT(*)
    FROM bronze.binance_klines
    GROUP BY symbol
    ORDER BY symbol
    """
)
now = datetime.now(timezone.utc)
window_start = now - timedelta(days=history_days + 1)
print("\n[5] Temporal range check...")
for symbol, min_ot, max_ot, cnt in ranges:
    print(f"    {symbol}: min={min_ot} max={max_ot} count={cnt}")
    assert min_ot >= window_start.replace(tzinfo=min_ot.tzinfo), (
        f"{symbol} min open_time older than expected history window"
    )
    assert max_ot <= now + timedelta(minutes=5)
    span = max_ot - min_ot
    assert span.total_seconds() >= (history_days - 1) * 86400, (
        f"{symbol} span too short for history_days={history_days}: {span}"
    )

print("\n[6] Second Bootstrap run (must not re-download full history)...")
count_before = total_klines
pipeline2 = BootstrapPipeline()
run_id_2 = "bootstrap_it_rerun_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
rows_2 = pipeline2.run(run_id_2)
count_after = _count_klines()

print(f"    rows_submitted={rows_2}")
print(f"    klines before={count_before} after={count_after}")

assert rows_2 == 0, "second run should skip completed symbols (no re-download)"
assert count_after == count_before, "klines must not be duplicated on re-run"
assert count_after == expected_rows

statuses = _fetch_all(
    "SELECT symbol, bootstrap_status FROM bronze.configured_symbols ORDER BY symbol"
)
for symbol, status in statuses:
    assert status == "completed"

print("\n" + "=" * 80)
print("BOOTSTRAP INTEGRATION TEST PASSED")
print("=" * 80)
