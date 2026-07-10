"""Convert candle interval strings to Airflow cron schedules."""

from __future__ import annotations

# Maps project interval labels (config.yaml) to standard 5-field cron.
_INTERVAL_TO_CRON: dict[str, str] = {
    "1m": "* * * * *",
    "5m": "*/5 * * * *",
    "15m": "*/15 * * * *",
    "30m": "*/30 * * * *",
    "1h": "0 * * * *",
    "1d": "0 0 * * *",
}


def interval_to_cron(interval: str) -> str:
    """
    Convert a market data interval to an Airflow cron expression.

    Supported intervals: 1m, 5m, 15m, 30m, 1h, 1d.

    Args:
        interval: Interval label as stored in config.yaml
            (e.g. sources.binance.historical.interval).

    Returns:
        Five-field cron string for Airflow ``schedule``.

    Raises:
        ValueError: If the interval is not supported.
    """
    key = (interval or "").strip().lower()
    if key not in _INTERVAL_TO_CRON:
        supported = ", ".join(sorted(_INTERVAL_TO_CRON))
        raise ValueError(
            f"Unsupported interval {interval!r}. Supported values: {supported}."
        )
    return _INTERVAL_TO_CRON[key]


def supported_intervals() -> tuple[str, ...]:
    """Return the list of intervals that can be converted to cron."""
    return tuple(_INTERVAL_TO_CRON.keys())
