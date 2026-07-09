import subprocess
from datetime import datetime, timedelta, timezone

from src.pipelines.bronze_pipeline import BronzePipeline
from src.common.database import Database

TEST_KLINES = 3000

TIMEFRAMES = ("5m", "15m", "30m", "1h", "1d")


def get_count(query: str) -> int:
    connection = Database().get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()[0]
    finally:
        connection.close()


def run_dbt_step(args: list[str], section_name: str):
    print("=" * 80)
    print(section_name)
    print("=" * 80)

    result = subprocess.run(
        ["dbt"] + args,
        cwd="dbt",
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(f"dbt {' '.join(args)} failed")

    output = result.stdout.strip()
    if output:
        print(output[-2000:] if len(output) > 2000 else output)

    print()


def seed_test_klines():
    print("=" * 80)
    print(f"SEEDING ADDITIONAL TEST DATA FOR FULL AGGREGATIONS ({TEST_KLINES} 1m klines)")
    print("=" * 80)

    conn = Database().get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bronze.pipeline_runs (dag_run_id, started_at, status, rows_inserted)
                VALUES ('e2e-test-seed', NOW(), 'success', 0)
                ON CONFLICT (dag_run_id) DO UPDATE SET started_at = NOW()
                RETURNING pipeline_run_id
            """)
            run_id = cur.fetchone()[0]

            cur.execute("""
                DELETE FROM bronze.binance_klines 
                WHERE symbol = 'BTCUSDT' 
                  AND open_time >= '2026-07-01 00:00:00+00'
            """)

            base_time = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
            for i in range(TEST_KLINES):
                open_t = base_time + timedelta(minutes=i)
                close_t = open_t + timedelta(minutes=1)
                cur.execute("""
                    INSERT INTO bronze.binance_klines (
                        pipeline_run_id, symbol, open_time, close_time,
                        open_price, high_price, low_price, close_price,
                        volume, quote_asset_volume, number_of_trades,
                        taker_buy_base_volume, taker_buy_quote_volume
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    run_id, 'BTCUSDT', open_t, close_t,
                    60000 + (i % 100), 60010 + (i % 100), 59990 + (i % 50), 60005 + (i % 80),
                    100 + (i % 50), 6000000 + (i % 1000) * 1000, 50 + (i % 30),
                    40 + (i % 20), 2400000 + (i % 50) * 500
                ))
            conn.commit()
        print(f"Seeded {TEST_KLINES} consecutive 1m klines for BTCUSDT to populate all timeframes")
    except Exception as e:
        conn.rollback()
        print(f"Warning: could not seed extra data: {e}")
    finally:
        conn.close()

    print()


print("=" * 80)
print("RUNNING BRONZE PIPELINE")
print("=" * 80)

pipeline = BronzePipeline()
dag_run_id = "integration_test_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
rows_inserted = pipeline.run(dag_run_id)
print(f"Rows inserted into Bronze (dag_run_id={dag_run_id}): {rows_inserted}")

print()

seed_test_klines()


run_dbt_step(
    ["build"],
    "RUNNING DBT BUILD"
)

# ---------------------------------------------------------------------------
# BRONZE
# ---------------------------------------------------------------------------
print("=" * 80)
print("BRONZE")
print("=" * 80)

bronze_price = get_count("SELECT COUNT(*) FROM bronze.binance_price;")
bronze_ticker = get_count("SELECT COUNT(*) FROM bronze.binance_ticker_24h;")
bronze_klines = get_count("SELECT COUNT(*) FROM bronze.binance_klines;")

print(f"Bronze Price         : {bronze_price}")
print(f"Bronze Ticker 24h    : {bronze_ticker}")
print(f"Bronze Klines        : {bronze_klines}")

assert bronze_price > 0, "No records in bronze.binance_price"
assert bronze_ticker > 0, "No records in bronze.binance_ticker_24h"
assert bronze_klines > 0, "No records in bronze.binance_klines"

print()

# ---------------------------------------------------------------------------
# SILVER
# ---------------------------------------------------------------------------
print("=" * 80)
print("SILVER")
print("=" * 80)

silver_snapshot = get_count("SELECT COUNT(*) FROM silver.market_snapshot;")
silver_candles = get_count("SELECT COUNT(*) FROM silver.market_candles;")
silver_candles_5m = get_count("SELECT COUNT(*) FROM silver.market_candles_5m;")
silver_candles_15m = get_count("SELECT COUNT(*) FROM silver.market_candles_15m;")
silver_candles_30m = get_count("SELECT COUNT(*) FROM silver.market_candles_30m;")
silver_candles_1h = get_count("SELECT COUNT(*) FROM silver.market_candles_1h;")
silver_candles_1d = get_count("SELECT COUNT(*) FROM silver.market_candles_1d;")

print(f"Silver Snapshot      : {silver_snapshot}")
print(f"Silver Candles 1m    : {silver_candles}")
print(f"Silver Candles 5m    : {silver_candles_5m}")
print(f"Silver Candles 15m   : {silver_candles_15m}")
print(f"Silver Candles 30m   : {silver_candles_30m}")
print(f"Silver Candles 1h    : {silver_candles_1h}")
print(f"Silver Candles 1d    : {silver_candles_1d}")

assert silver_snapshot > 0
assert silver_candles > 0
assert silver_candles_5m > 0
assert silver_candles_15m > 0
assert silver_candles_30m > 0
assert silver_candles_1h > 0
assert silver_candles_1d > 0

print()

# ---------------------------------------------------------------------------
# INDICATORS
# ---------------------------------------------------------------------------
print("=" * 80)
print("INDICATORS")
print("=" * 80)

indicators = {
    tf: get_count(f"SELECT COUNT(*) FROM gold.market_indicators_{tf};")
    for tf in TIMEFRAMES
}

for tf in TIMEFRAMES:
    print(f"Gold Indicators {tf:3} : {indicators[tf]}")

for tf in TIMEFRAMES:
    assert indicators[tf] > 0, f"No records in gold.market_indicators_{tf}"

print()

# ---------------------------------------------------------------------------
# FEATURES
# ---------------------------------------------------------------------------
print("=" * 80)
print("FEATURES")
print("=" * 80)

features = {
    tf: get_count(f"SELECT COUNT(*) FROM gold.market_features_{tf};")
    for tf in TIMEFRAMES
}

for tf in TIMEFRAMES:
    print(f"Gold Features {tf:3}   : {features[tf]}")

for tf in TIMEFRAMES:
    assert features[tf] > 0, f"No records in gold.market_features_{tf}"

print()

# ---------------------------------------------------------------------------
# SIGNALS
# ---------------------------------------------------------------------------
print("=" * 80)
print("SIGNALS")
print("=" * 80)

signals = {
    tf: get_count(f"SELECT COUNT(*) FROM gold.market_signals_{tf};")
    for tf in TIMEFRAMES
}

for tf in TIMEFRAMES:
    print(f"Gold Signals {tf:3}    : {signals[tf]}")

for tf in TIMEFRAMES:
    assert signals[tf] > 0, f"No records in gold.market_signals_{tf}"

print()

# ---------------------------------------------------------------------------
# FEATURE TABLES
# ---------------------------------------------------------------------------
print("=" * 80)
print("FEATURE TABLES")
print("=" * 80)

datasets = {
    tf: get_count(f"SELECT COUNT(*) FROM gold.market_dataset_{tf};")
    for tf in TIMEFRAMES
}

for tf in TIMEFRAMES:
    print(f"Gold Dataset {tf:3}    : {datasets[tf]}")

for tf in TIMEFRAMES:
    assert datasets[tf] > 0, f"No records in gold.market_dataset_{tf}"

print()

# ---------------------------------------------------------------------------
# CONSISTENCY CHECKS
# Indicators == Features == Signals == Dataset per timeframe
# ---------------------------------------------------------------------------
print("=" * 80)
print("CONSISTENCY CHECKS")
print("=" * 80)

for tf in TIMEFRAMES:
    ind = indicators[tf]
    feat = features[tf]
    sig = signals[tf]
    ds = datasets[tf]

    print(
        f"{tf:3}  indicators={ind}  features={feat}  signals={sig}  dataset={ds}"
    )

    assert ind == feat, (
        f"Row count mismatch for {tf}: indicators ({ind}) != features ({feat})"
    )
    assert feat == sig, (
        f"Row count mismatch for {tf}: features ({feat}) != signals ({sig})"
    )
    assert sig == ds, (
        f"Row count mismatch for {tf}: signals ({sig}) != dataset ({ds})"
    )

print()
print("All timeframes: Indicators == Features == Signals == Dataset")
print()

print("=" * 80)
print("PASSED")
print("=" * 80)
