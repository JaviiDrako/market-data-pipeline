from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MarketDataExtractor(ABC):
    """Common extraction operations shared by Bronze and Bootstrap pipelines."""

    @abstractmethod
    def extract_klines(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1,
        symbols: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract klines for the given symbols.

        When start_time and end_time are omitted, returns the most recent closed
        candle(s) up to ``limit`` per symbol (same behaviour as the historical
        incremental extract).

        When dates are provided, returns candles in that range (at most
        ``limit`` rows per request; callers paginate for full history).

        Args:
            start_time: Inclusive start as Unix milliseconds (optional).
            end_time: Inclusive end as Unix milliseconds (optional).
            limit: Max candles per symbol for this request.
            symbols: Symbols to extract; defaults to configured source symbols.
        """

    @abstractmethod
    def extract_current_price(self) -> list[dict[str, Any]]:
        """Extract current prices for configured symbols."""

    @abstractmethod
    def extract_ticker_24h(self) -> list[dict[str, Any]]:
        """Extract 24-hour ticker data for configured symbols."""
