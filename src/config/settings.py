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