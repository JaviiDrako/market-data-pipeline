from __future__ import annotations

from typing import Any

from src.clients.binance.client import BinanceClient
from src.config.settings import Settings


class BinanceExtractor:
    """Extracts Binance market data using configured symbols."""

    def __init__(self, settings: Settings, client: BinanceClient) -> None:
        self._settings = settings
        self._client = client

        self._source = self._settings.get_source("binance")
        self._symbols: list[str] = self._source.get("symbols", [])

        klines = self._source.get("historical", {})
        self._interval: str = klines.get("interval", "1m")

    def extract_latest_klines(self) -> list[dict[str, Any]]:
        """Extract the latest closed kline for every configured symbol."""

        extracted_data: list[dict[str, Any]] = []

        for symbol in self._symbols:
            klines = self._client.get_historical_klines(
                symbol=symbol,
                interval=self._interval,
                limit=1,
            )

            for kline in klines:
                extracted_data.append(
                    {
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
                )

        return extracted_data

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