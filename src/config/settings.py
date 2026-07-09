from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class Settings:
    """Loads and exposes application settings from config.yaml."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = (
            Path(config_path)
            if config_path
            else Path(__file__).with_name("config.yaml")
        )
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load the YAML configuration file."""
        with self._config_path.open("r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or {}

    @property
    def database(self) -> dict[str, Any]:
        """Return database configuration."""
        return self._config.get("database", {})

    @property
    def quality(self) -> dict[str, Any]:
        """Return data quality configuration."""
        return self._config.get("quality", {})

    @property
    def sources(self) -> dict[str, Any]:
        """Return all configured data sources."""
        return self._config.get("sources", {})

    def get_source(self, source_name: str) -> dict[str, Any]:
        """
        Return the configuration for a specific data source.

        Example:
            settings.get_source("binance")
            settings.get_source("yahoo")
        """
        return self.sources.get(source_name, {})

    def get_symbols(self, source_name: str) -> list[str]:
        """Return configured trading symbols for a data source."""
        symbols = self.get_source(source_name).get("symbols", [])
        return list(symbols) if symbols else []

    def get_historical(self, source_name: str) -> dict[str, Any]:
        """
        Return historical bootstrap settings for a data source.

        Reads ``sources.<source>.historical`` from config.yaml.

        Returns:
            dict with:
            - days (int): depth of history to load (default 365)
            - interval (str): candle interval, e.g. ``1m`` (default ``1m``)
        """
        historical = self.get_source(source_name).get("historical") or {}
        return {
            "days": int(historical.get("days", 365)),
            "interval": str(historical.get("interval", "1m")),
        }

    def get_history_days(self, source_name: str) -> int:
        """Return historical depth in days for a data source."""
        return int(self.get_historical(source_name)["days"])

    def get_history_interval(self, source_name: str) -> str:
        """Return historical candle interval for a data source."""
        return str(self.get_historical(source_name)["interval"])