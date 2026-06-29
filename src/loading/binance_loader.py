from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from src.common.database import Database


class BinanceLoader:
    """Persists extracted Binance data into the Bronze layer."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def insert_current_prices(
        self,
        records: list[dict[str, Any]],
        pipeline_run_id: int,
    ) -> int:
        """Insert current price records into bronze.binance_price."""
        if not records:
            return 0

        query = """
            INSERT INTO bronze.binance_price (
                pipeline_run_id,
                symbol,
                price
            )
            VALUES (%s, %s, %s)
        """

        values = [
            (
                pipeline_run_id,
                record["symbol"],
                self._to_decimal(record["price"]),
            )
            for record in records
        ]

        self._execute_many(query, values)
        return len(records)

    def insert_ticker_24h(
        self,
        records: list[dict[str, Any]],
        pipeline_run_id: int,
    ) -> int:
        """Insert 24-hour ticker records into bronze.binance_ticker_24h."""
        if not records:
            return 0

        query = """
            INSERT INTO bronze.binance_ticker_24h (
                pipeline_run_id,
                symbol,
                price_change,
                price_change_percent,
                weighted_avg_price,
                prev_close_price,
                last_price,
                last_qty,
                bid_price,
                bid_qty,
                ask_price,
                ask_qty,
                open_price,
                high_price,
                low_price,
                volume,
                quote_volume,
                open_time,
                close_time,
                first_id,
                last_id,
                count
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        values = [
            (
                pipeline_run_id,
                record["symbol"],
                self._to_decimal(record["price_change"]),
                self._to_decimal(record["price_change_percent"]),
                self._to_decimal(record["weighted_avg_price"]),
                self._to_decimal(record["prev_close_price"]),
                self._to_decimal(record["last_price"]),
                self._to_decimal(record["last_qty"]),
                self._to_decimal(record["bid_price"]),
                self._to_decimal(record["bid_qty"]),
                self._to_decimal(record["ask_price"]),
                self._to_decimal(record["ask_qty"]),
                self._to_decimal(record["open_price"]),
                self._to_decimal(record["high_price"]),
                self._to_decimal(record["low_price"]),
                self._to_decimal(record["volume"]),
                self._to_decimal(record["quote_volume"]),
                self._to_timestamp(record["open_time"]),
                self._to_timestamp(record["close_time"]),
                int(record["first_id"]),
                int(record["last_id"]),
                int(record["count"]),
            )
            for record in records
        ]

        self._execute_many(query, values)
        return len(records)

    def insert_klines(
        self,
        records: list[dict[str, Any]],
        pipeline_run_id: int,
    ) -> int:
        """Insert historical kline records into bronze.binance_klines."""
        if not records:
            return 0

        query = """
            INSERT INTO bronze.binance_klines (
                pipeline_run_id,
                symbol,
                open_time,
                close_time,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                quote_asset_volume,
                number_of_trades,
                taker_buy_base_volume,
                taker_buy_quote_volume
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = [
            (
                pipeline_run_id,
                record["symbol"],
                self._to_timestamp(record["open_time"]),
                self._to_timestamp(record["close_time"]),
                self._to_decimal(record["open_price"]),
                self._to_decimal(record["high_price"]),
                self._to_decimal(record["low_price"]),
                self._to_decimal(record["close_price"]),
                self._to_decimal(record["volume"]),
                self._to_decimal(record["quote_asset_volume"]),
                int(record["number_of_trades"]),
                self._to_decimal(record["taker_buy_base_asset_volume"]),
                self._to_decimal(record["taker_buy_quote_asset_volume"]),
            )
            for record in records
        ]

        self._execute_many(query, values)
        return len(records)

    def _execute_many(self, query: str, values: Iterable[tuple[Any, ...]]) -> None:
        connection = self._database.get_connection()

        try:
            with connection.cursor() as cursor:
                cursor.executemany(query, values)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        return value if isinstance(value, Decimal) else Decimal(str(value))

    @staticmethod
    def _to_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

        if isinstance(value, int):
            seconds, milliseconds = divmod(value, 1000)
            return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
                microsecond=milliseconds * 1000
            )

        if isinstance(value, str):
            normalized_value = value.replace("Z", "+00:00")
            timestamp = datetime.fromisoformat(normalized_value)
            return (
                timestamp
                if timestamp.tzinfo
                else timestamp.replace(tzinfo=timezone.utc)
            )

        raise TypeError(f"Unsupported timestamp value: {value!r}")