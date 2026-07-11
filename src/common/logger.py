"""Centralized logging helpers for the Market Data Pipeline.

Uses the standard library ``logging`` module so messages integrate cleanly
with Airflow task logs and local CLI runs.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger for project components.

    Prefer module names, e.g. ``get_logger(__name__)``, so Airflow and local
    runs show a consistent hierarchy under ``src.*``.
    """
    configure_logging()
    return logging.getLogger(name)


def configure_logging(level: str | None = None) -> None:
    """
    Idempotent logging setup for CLI and container environments.

    When Airflow (or another host) has already configured the root logger,
    only the project log level is adjusted — no duplicate handlers are added.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    resolved_level_name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    resolved_level = getattr(logging, resolved_level_name, logging.INFO)

    root = logging.getLogger()

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT)
        )
        root.addHandler(handler)
        root.setLevel(resolved_level)
    elif root.level == logging.NOTSET:
        root.setLevel(resolved_level)

    # Ensure package loggers emit at the configured level under Airflow.
    logging.getLogger("src").setLevel(resolved_level)
    logging.getLogger("airflow.task").setLevel(logging.INFO)

    _CONFIGURED = True
