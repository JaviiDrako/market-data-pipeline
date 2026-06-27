from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MarketDataClient(ABC):
    """Abstract interface for market data providers."""

    @abstractmethod
    def get_historical_klines(self, symbol: str, interval: str, start_time: int, end_time: int | None = None) -> Any:
        """Fetches historical kline data."""

    @abstractmethod
    def get_current_price(self, symbol: str) -> Any:
        """Fetches the current price for a symbol."""

    @abstractmethod
    def get_ticker_24h(self, symbol: str) -> Any:
        """Fetches the 24h ticker data for a symbol."""
