from __future__ import annotations

from typing import Any

import requests

from src.clients.binance.settings import (
    API_VERSION,
    BASE_URL,
    DEFAULT_TIMEOUT,
    KLINES_ENDPOINT,
    PRICE_ENDPOINT,
    TICKER_24H_ENDPOINT,
)
from src.clients.market_data_client import MarketDataClient


class BinanceClientError(Exception):
    """Raised when the Binance API request fails."""


class BinanceClient(MarketDataClient):
    """REST client for Binance market data endpoints."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> Any:
        """Fetches historical klines from Binance."""
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
        }

        if start_time is not None:
            params["startTime"] = start_time

        if end_time is not None:
            params["endTime"] = end_time

        if limit is not None:
            params["limit"] = limit

        return self._get(KLINES_ENDPOINT, params)

    def get_current_price(self, symbol: str) -> Any:
        """Fetches the current symbol price from Binance."""
        return self._get(PRICE_ENDPOINT, {"symbol": symbol})

    def get_ticker_24h(self, symbol: str) -> Any:
        """Fetches the 24-hour ticker for a symbol from Binance."""
        return self._get(TICKER_24H_ENDPOINT, {"symbol": symbol})

    def _get(self, endpoint: str, params: dict[str, Any]) -> Any:
        url = f"{BASE_URL}{API_VERSION}{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
        except requests.HTTPError as exc:
            message = self._build_http_error_message(response)
            raise BinanceClientError(message) from exc
        except requests.RequestException as exc:
            raise BinanceClientError(f"Binance API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise BinanceClientError("Binance API returned a non-JSON response.") from exc

    @staticmethod
    def _build_http_error_message(response: requests.Response) -> str:
        try:
            error_body = response.json()
        except ValueError:
            error_body = response.text or "No response body."

        return (
            f"Binance API request failed with status {response.status_code}: "
            f"{error_body}"
        )
