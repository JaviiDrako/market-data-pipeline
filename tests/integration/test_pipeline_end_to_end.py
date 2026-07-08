import subprocess

from src.pipelines.bronze_pipeline import BronzePipeline
from src.common.database import Database


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

    # Print last part of output for visibility
    output = result.stdout.strip()
    if output:
        print(output[-2000:] if len(output) > 2000 else output)

    print()


print("=" * 80)
print("RUNNING BRONZE PIPELINE")
print("=" * 80)

pipeline = BronzePipeline()
rows_inserted = pipeline.run("integration_test")
print(f"Rows inserted into Bronze: {rows_inserted}")
print()

# dbt compile
run_dbt_step(["compile"], "RUNNING DBT COMPILE")

# dbt run silver + gold
run_dbt_step(["run", "--select", "silver gold"], "RUNNING DBT SILVER + GOLD")

# dbt test silver + gold
run_dbt_step(["test", "--select", "silver gold"], "RUNNING DBT TESTS")

print("=" * 80)
print("VERIFYING BRONZE")
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

print("=" * 80)
print("VERIFYING SILVER")
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

print("=" * 80)
print("VERIFYING GOLD")
print("=" * 80)

gold_5m = get_count("SELECT COUNT(*) FROM gold.market_indicators_5m;")
gold_15m = get_count("SELECT COUNT(*) FROM gold.market_indicators_15m;")
gold_30m = get_count("SELECT COUNT(*) FROM gold.market_indicators_30m;")
gold_1h = get_count("SELECT COUNT(*) FROM gold.market_indicators_1h;")
gold_1d = get_count("SELECT COUNT(*) FROM gold.market_indicators_1d;")

print(f"Gold Indicators 5m   : {gold_5m}")
print(f"Gold Indicators 15m  : {gold_15m}")
print(f"Gold Indicators 30m  : {gold_30m}")
print(f"Gold Indicators 1h   : {gold_1h}")
print(f"Gold Indicators 1d   : {gold_1d}")

assert gold_5m > 0
assert gold_15m > 0
assert gold_30m > 0
assert gold_1h > 0
assert gold_1d > 0

print()

print("=" * 80)
print("PIPELINE END-TO-END TEST PASSED")
print("=" * 80)