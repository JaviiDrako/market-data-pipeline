"""
Integration test: mathematical correctness of 1m → 5m OHLCV aggregation.

Uses a deterministic set of five 1-minute candles that form exactly one
complete 5-minute bucket, then runs dbt and asserts open/high/low/close/volume.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.common.database import Database

# Unique symbol so this test does not collide with live/bootstrap data.
TEST_SYMBOL = "AGGTEST5M"
TEST_EXCHANGE = "BINANCE"

# Fixed 5m bucket start (aligned to 5-minute boundary).
BUCKET_START = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

# Deterministic 1m candles (open_time = BUCKET_START + i minutes).
# Columns: open, high, low, close, volume
CANDLES_1M = [
    # open  high  low   close  volume
    (Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"), Decimal("10")),
    (Decimal("105"), Decimal("115"), Decimal("100"), Decimal("110"), Decimal("20")),
    (Decimal("110"), Decimal("120"), Decimal("105"), Decimal("108"), Decimal("30")),
    (Decimal("108"), Decimal("112"), Decimal("95"), Decimal("100"), Decimal("15")),
    (Decimal("100"), Decimal("105"), Decimal("98"), Decimal("102"), Decimal("25")),
]

# Expected 5m OHLCV from aggregate_ohlcv macro:
# open  = first open by open_time ASC
# high  = max(high)
# low   = min(low)
# close = last close by open_time DESC
# volume = sum(volume)
EXPECTED_5M = {
    "open_price": Decimal("100"),
    "high_price": Decimal("120"),
    "low_price": Decimal("90"),
    "close_price": Decimal("102"),
    "volume": Decimal("100"),  # 10+20+30+15+25
}


def _conn():
    return Database().get_connection()


def _execute(query: str, params: tuple = ()) -> None:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _fetch_one(query: str, params: tuple = (), *, commit: bool = False):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        if commit:
            conn.commit()
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _cleanup_test_symbol() -> None:
    """Remove only AGGTEST5M rows (does not wipe the whole warehouse)."""
    _execute(
        "DELETE FROM bronze.binance_klines WHERE symbol = %s",
        (TEST_SYMBOL,),
    )
    # Silver / gold may not have the symbol yet; ignore missing-table races.
    for table in (
        "silver.market_candles",
        "silver.market_candles_5m",
    ):
        try:
            _execute(f"DELETE FROM {table} WHERE symbol = %s", (TEST_SYMBOL,))
        except Exception:
            pass


def _seed_pipeline_run() -> int:
    dag_run_id = "agg_test_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    row = _fetch_one(
        """
        INSERT INTO bronze.pipeline_runs (dag_run_id, started_at, finished_at, status, rows_inserted)
        VALUES (%s, NOW(), NOW(), 'success', 5)
        RETURNING pipeline_run_id
        """,
        (dag_run_id,),
        commit=True,
    )
    if row is None:
        raise RuntimeError("Failed to create pipeline_runs row for aggregation test")
    return int(row[0])


def _seed_1m_klines(pipeline_run_id: int) -> None:
    for i, (o, h, l, c, v) in enumerate(CANDLES_1M):
        open_t = BUCKET_START + timedelta(minutes=i)
        close_t = open_t + timedelta(minutes=1) - timedelta(milliseconds=1)
        _execute(
            """
            INSERT INTO bronze.binance_klines (
                pipeline_run_id, symbol, open_time, close_time,
                open_price, high_price, low_price, close_price,
                volume, quote_asset_volume, number_of_trades,
                taker_buy_base_volume, taker_buy_quote_volume
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (symbol, open_time) DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume
            """,
            (
                pipeline_run_id,
                TEST_SYMBOL,
                open_t,
                close_t,
                o,
                h,
                l,
                c,
                v,
                v * 100,  # quote_asset_volume placeholder
                5,
                v / 2,
                v * 50,
            ),
        )


def _run_dbt_aggregation_models() -> None:
    """Build 1m candles + 5m aggregation (full-refresh so new symbol is included)."""
    result = subprocess.run(
        [
            "dbt",
            "run",
            "--project-dir",
            "dbt",
            "--profiles-dir",
            "dbt",
            "--full-refresh",
            "--select",
            "stg_binance_klines market_candles market_candles_5m",
        ],
        capture_output=True,
        text=True,
        cwd=".",
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("dbt run for aggregation models failed")
    print(result.stdout[-1500:] if result.stdout else "")


def _as_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


print("=" * 80)
print("AGGREGATION 1m → 5m MATHEMATICAL TEST")
print("=" * 80)

print("\n[1] Cleanup previous AGGTEST5M rows...")
_cleanup_test_symbol()

print("\n[2] Seed deterministic 5×1m candles...")
run_id = _seed_pipeline_run()
_seed_1m_klines(run_id)
bronze_count = _fetch_one(
    "SELECT COUNT(*) FROM bronze.binance_klines WHERE symbol = %s",
    (TEST_SYMBOL,),
)[0]
assert bronze_count == 5, f"expected 5 bronze klines, got {bronze_count}"
print(f"    Seeded {bronze_count} 1m klines for {TEST_SYMBOL} at {BUCKET_START.isoformat()}")

print("\n[3] Run dbt (market_candles + market_candles_5m full-refresh)...")
_run_dbt_aggregation_models()

print("\n[4] Assert 1m silver row count...")
silver_1m = _fetch_one(
    """
    SELECT COUNT(*) FROM silver.market_candles
    WHERE symbol = %s AND interval = '1m'
    """,
    (TEST_SYMBOL,),
)[0]
assert silver_1m == 5, f"expected 5 silver 1m candles, got {silver_1m}"

print("\n[5] Assert 5m OHLCV matches expected math...")
row = _fetch_one(
    """
    SELECT open_time, open_price, high_price, low_price, close_price, volume
    FROM silver.market_candles_5m
    WHERE symbol = %s
    ORDER BY open_time
    """,
    (TEST_SYMBOL,),
)
assert row is not None, f"no 5m candle found for {TEST_SYMBOL}"

open_time, open_p, high_p, low_p, close_p, volume = row
print(f"    open_time   = {open_time}")
print(f"    open_price  = {open_p}  (expected {EXPECTED_5M['open_price']})")
print(f"    high_price  = {high_p}  (expected {EXPECTED_5M['high_price']})")
print(f"    low_price   = {low_p}  (expected {EXPECTED_5M['low_price']})")
print(f"    close_price = {close_p}  (expected {EXPECTED_5M['close_price']})")
print(f"    volume      = {volume}  (expected {EXPECTED_5M['volume']})")

# Bucket open must match our aligned start (allow DB timezone normalization).
assert open_time.replace(tzinfo=timezone.utc) == BUCKET_START or (
    open_time.astimezone(timezone.utc) == BUCKET_START
), f"unexpected 5m open_time {open_time}"

assert _as_decimal(open_p) == EXPECTED_5M["open_price"]
assert _as_decimal(high_p) == EXPECTED_5M["high_price"]
assert _as_decimal(low_p) == EXPECTED_5M["low_price"]
assert _as_decimal(close_p) == EXPECTED_5M["close_price"]
assert _as_decimal(volume) == EXPECTED_5M["volume"]

# Exactly one complete 5m bar for this symbol
five_m_count = _fetch_one(
    "SELECT COUNT(*) FROM silver.market_candles_5m WHERE symbol = %s",
    (TEST_SYMBOL,),
)[0]
assert five_m_count == 1, f"expected exactly 1 five-minute bar, got {five_m_count}"

print("\n[6] Cleanup test symbol...")
_cleanup_test_symbol()

print("\n" + "=" * 80)
print("AGGREGATION 1m → 5m TEST PASSED")
print("=" * 80)
