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


print("=" * 80)
print("RUNNING BRONZE PIPELINE")
print("=" * 80)

pipeline = BronzePipeline()

rows_inserted = pipeline.run("integration_test")

print(f"Rows inserted into Bronze: {rows_inserted}")

print()

print("=" * 80)
print("RUNNING DBT")
print("=" * 80)

result = subprocess.run(
    ["dbt", "run"],
    cwd="dbt",
)

if result.returncode != 0:
    raise RuntimeError("dbt run failed.")

print()

print("=" * 80)
print("VERIFYING DATA")
print("=" * 80)

bronze_price = get_count(
    "SELECT COUNT(*) FROM bronze.binance_price;"
)

bronze_ticker = get_count(
    "SELECT COUNT(*) FROM bronze.binance_ticker_24h;"
)

bronze_klines = get_count(
    "SELECT COUNT(*) FROM bronze.binance_klines;"
)

silver_candles = get_count(
    "SELECT COUNT(*) FROM silver.market_candles;"
)

silver_snapshot = get_count(
    "SELECT COUNT(*) FROM silver.market_snapshot;"
)

print(f"Bronze Price      : {bronze_price}")
print(f"Bronze Ticker     : {bronze_ticker}")
print(f"Bronze Klines     : {bronze_klines}")
print(f"Silver Candles    : {silver_candles}")
print(f"Silver Snapshot   : {silver_snapshot}")

assert bronze_price > 0
assert bronze_ticker > 0
assert bronze_klines > 0
assert silver_candles > 0
assert silver_snapshot > 0

print()
print("=" * 80)
print("INTEGRATION TEST PASSED")
print("=" * 80)