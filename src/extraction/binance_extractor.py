from __future__ import annotations

from typing import Any

from src.clients.binance.client import BinanceClient
from src.config.settings import Settings
from src.extraction.market_data_extractor import MarketDataExtractor

# Binance GET /api/v3/klines hard limit: max 1000 candles per request.
# See: https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
BINANCE_KLINES_MAX_LIMIT = 1000


class BinanceExtractor(MarketDataExtractor):
    """Extracts Binance market data using configured symbols."""

    def __init__(self, settings: Settings, client: BinanceClient) -> None:
        self._settings = settings
        self._client = client

        self._symbols: list[str] = self._settings.get_symbols("binance")
        self._interval: str = self._settings.get_history_interval("binance")

    def extract_klines(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1,
        symbols: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract klines for one or more symbols.

        Without start_time/end_time this matches the previous extract_latest_klines
        behaviour (latest closed candle when limit=1).

        With dates, returns at most ``limit`` candles per symbol for that range.
        Callers that need full history must paginate using BINANCE_KLINES_MAX_LIMIT.
        """
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if limit > BINANCE_KLINES_MAX_LIMIT:
            raise ValueError(
                f"limit cannot exceed Binance max of {BINANCE_KLINES_MAX_LIMIT} klines per request"
            )

        target_symbols = symbols if symbols is not None else self._symbols
        extracted_data: list[dict[str, Any]] = []

        for symbol in target_symbols:
            klines = self._client.get_historical_klines(
                symbol=symbol,
                interval=self._interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )

            for kline in klines:
                extracted_data.append(self._map_kline(symbol, kline))

        return extracted_data

    def extract_latest_klines(self) -> list[dict[str, Any]]:
        """Backward-compatible alias: latest closed kline per configured symbol."""
        return self.extract_klines(limit=1)

    def extract_current_price(self) -> list[dict[str, Any]]:
        """Extract current prices for configured symbols."""

        extracted_data: list[dict[str, Any]] = []

        for symbol in self._symbols:
            price_data = self._client.get_current_price(symbol)

            extracted_data.append(
                {
                    "symbol": price_data["symbol"],
                    "price": price_data["price"],
                }
            )

        return extracted_data

    def extract_ticker_24h(self) -> list[dict[str, Any]]:
        """Extract 24-hour ticker data for configured symbols."""

        extracted_data: list[dict[str, Any]] = []

        for symbol in self._symbols:
            ticker_data = self._client.get_ticker_24h(symbol)

            extracted_data.append(
                {
                    "symbol": ticker_data["symbol"],
                    "price_change": ticker_data["priceChange"],
                    "price_change_percent": ticker_data["priceChangePercent"],
                    "weighted_avg_price": ticker_data["weightedAvgPrice"],
                    "prev_close_price": ticker_data["prevClosePrice"],
                    "last_price": ticker_data["lastPrice"],
                    "last_qty": ticker_data["lastQty"],
                    "bid_price": ticker_data["bidPrice"],
                    "bid_qty": ticker_data["bidQty"],
                    "ask_price": ticker_data["askPrice"],
                    "ask_qty": ticker_data["askQty"],
                    "open_price": ticker_data["openPrice"],
                    "high_price": ticker_data["highPrice"],
                    "low_price": ticker_data["lowPrice"],
                    "volume": ticker_data["volume"],
                    "quote_volume": ticker_data["quoteVolume"],
                    "open_time": ticker_data["openTime"],
                    "close_time": ticker_data["closeTime"],
                    "first_id": ticker_data["firstId"],
                    "last_id": ticker_data["lastId"],
                    "count": ticker_data["count"],
                }
            )

        return extracted_data

    @staticmethod
    def _map_kline(symbol: str, kline: list[Any]) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "open_time": kline[0],
            "open_price": kline[1],
            "high_price": kline[2],
            "low_price": kline[3],
            "close_price": kline[4],
            "volume": kline[5],
            "close_time": kline[6],
            "quote_asset_volume": kline[7],
            "number_of_trades": kline[8],
            "taker_buy_base_asset_volume": kline[9],
            "taker_buy_quote_asset_volume": kline[10],
        }
