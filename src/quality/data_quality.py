from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from src.common.exceptions import DataQualityError


class DataQuality:
    """Validates extracted records before Bronze persistence."""

    def validate_current_prices(self, records: list[dict[str, Any]]) -> None:
        """Validate extracted current price records."""
        for index, record in enumerate(records):
            self._require_symbol(record, index)
            price = self._require_decimal(record, "price", index)
            if price <= 0:
                raise DataQualityError(
                    f"Invalid current price at index {index}: price must be greater than 0."
                )

    def validate_ticker_24h(self, records: list[dict[str, Any]]) -> None:
        """Validate extracted 24-hour ticker records."""
        for index, record in enumerate(records):
            self._require_symbol(record, index)

            high_price = self._require_decimal(record, "high_price", index)
            low_price = self._require_decimal(record, "low_price", index)
            weighted_avg_price = self._require_decimal(record, "weighted_avg_price", index)
            prev_close_price = self._require_decimal(record, "prev_close_price", index)
            last_price = self._require_decimal(record, "last_price", index)
            bid_price = self._require_decimal(record, "bid_price", index)
            ask_price = self._require_decimal(record, "ask_price", index)
            volume = self._require_decimal(record, "volume", index)
            quote_volume = self._require_decimal(record, "quote_volume", index)
            count = self._require_non_negative_int(record, "count", index)
            open_time = self._require_timestamp(record, "open_time", index)
            close_time = self._require_timestamp(record, "close_time", index)

            if high_price < low_price:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: high_price must be greater than or equal to low_price."
                )
            if weighted_avg_price < 0:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: weighted_avg_price must be greater than or equal to 0."
                )
            if prev_close_price < 0:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: prev_close_price must be greater than or equal to 0."
                )
            if last_price < 0:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: last_price must be greater than or equal to 0."
                )
            if bid_price < 0:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: bid_price must be greater than or equal to 0."
                )
            if ask_price < 0:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: ask_price must be greater than or equal to 0."
                )
            if volume < 0:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: volume must be greater than or equal to 0."
                )
            if quote_volume < 0:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: quote_volume must be greater than or equal to 0."
                )
            if count < 0:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: count must be greater than or equal to 0."
                )
            if open_time >= close_time:
                raise DataQualityError(
                    f"Invalid ticker_24h record at index {index}: open_time must be earlier than close_time."
                )

    def validate_latest_klines(self, records: list[dict[str, Any]]) -> None:
        """Validate extracted latest kline records."""
        for index, record in enumerate(records):
            self._require_symbol(record, index)

            open_price = self._require_decimal(record, "open_price", index)
            high_price = self._require_decimal(record, "high_price", index)
            low_price = self._require_decimal(record, "low_price", index)
            close_price = self._require_decimal(record, "close_price", index)
            volume = self._require_decimal(record, "volume", index)
            quote_asset_volume = self._require_decimal(record, "quote_asset_volume", index)
            number_of_trades = self._require_non_negative_int(record, "number_of_trades", index)
            taker_buy_base_asset_volume = self._require_decimal(
                record,
                "taker_buy_base_asset_volume",
                index,
            )
            taker_buy_quote_asset_volume = self._require_decimal(
                record,
                "taker_buy_quote_asset_volume",
                index,
            )
            open_time = self._require_timestamp(record, "open_time", index)
            close_time = self._require_timestamp(record, "close_time", index)

            if open_price <= 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: open_price must be greater than 0."
                )
            if high_price <= 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: high_price must be greater than 0."
                )
            if low_price <= 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: low_price must be greater than 0."
                )
            if close_price <= 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: close_price must be greater than 0."
                )
            if high_price < low_price:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: high_price must be greater than or equal to low_price."
                )
            if volume < 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: volume must be greater than or equal to 0."
                )
            if quote_asset_volume < 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: quote_asset_volume must be greater than or equal to 0."
                )
            if number_of_trades < 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: number_of_trades must be greater than or equal to 0."
                )
            if taker_buy_base_asset_volume < 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: taker_buy_base_asset_volume must be greater than or equal to 0."
                )
            if taker_buy_quote_asset_volume < 0:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: taker_buy_quote_asset_volume must be greater than or equal to 0."
                )
            if open_time >= close_time:
                raise DataQualityError(
                    f"Invalid kline record at index {index}: open_time must be earlier than close_time."
                )

    def _require_symbol(self, record: dict[str, Any], index: int) -> str:
        symbol = record.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise DataQualityError(
                f"Invalid record at index {index}: symbol is required and must not be empty."
            )
        return symbol

    def _require_decimal(
        self,
        record: dict[str, Any],
        field_name: str,
        index: int,
    ) -> Decimal:
        if field_name not in record:
            raise DataQualityError(
                f"Invalid record at index {index}: {field_name} is required."
            )

        value = record[field_name]
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise DataQualityError(
                f"Invalid record at index {index}: {field_name} must be convertible to Decimal."
            ) from exc

        if not decimal_value.is_finite():
            raise DataQualityError(
                f"Invalid record at index {index}: {field_name} must be a finite Decimal value."
            )

        return decimal_value

    def _require_non_negative_int(
        self,
        record: dict[str, Any],
        field_name: str,
        index: int,
    ) -> int:
        if field_name not in record:
            raise DataQualityError(
                f"Invalid record at index {index}: {field_name} is required."
            )

        value = record[field_name]

        if isinstance(value, bool):
            raise DataQualityError(
                f"Invalid record at index {index}: {field_name} must be a valid integer."
            )

        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise DataQualityError(
                f"Invalid record at index {index}: {field_name} must be a valid integer."
            ) from exc

        if not decimal_value.is_finite() or decimal_value != decimal_value.to_integral_value():
            raise DataQualityError(
                f"Invalid record at index {index}: {field_name} must be a valid integer."
            )

        return int(decimal_value)

    def _require_timestamp(
        self,
        record: dict[str, Any],
        field_name: str,
        index: int,
    ) -> datetime:
        if field_name not in record:
            raise DataQualityError(
                f"Invalid record at index {index}: {field_name} is required."
            )

        value = record[field_name]

        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

        if isinstance(value, int) and not isinstance(value, bool):
            try:
                seconds, milliseconds = divmod(value, 1000)
                return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
                    microsecond=milliseconds * 1000
                )
            except (OverflowError, OSError, ValueError) as exc:
                raise DataQualityError(
                    f"Invalid record at index {index}: {field_name} must be a valid timestamp."
                ) from exc

        if isinstance(value, str):
            try:
                normalized_value = value.replace("Z", "+00:00")
                timestamp = datetime.fromisoformat(normalized_value)
            except ValueError as exc:
                raise DataQualityError(
                    f"Invalid record at index {index}: {field_name} must be a valid timestamp."
                ) from exc
            return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

        raise DataQualityError(
            f"Invalid record at index {index}: {field_name} must be a valid timestamp."
        )
