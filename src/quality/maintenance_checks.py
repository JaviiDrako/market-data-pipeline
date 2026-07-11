"""
Reusable data-quality checks for the Airflow Maintenance DAG.

These functions only *validate* warehouse state. They do not extract data,
run pipelines, or execute dbt.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.common.database import Database

logger = logging.getLogger(__name__)

# Maximum allowed lag between NOW() and MAX(open_time) on bronze.binance_klines.
# Incremental runs every interval (often 1m); 2 hours tolerates brief outages
# without false positives while still flagging a stuck pipeline.
BRONZE_FRESHNESS_MAX_AGE = timedelta(hours=2)

GOLD_5M_TABLES = (
    "market_indicators_5m",
    "market_features_5m",
    "market_signals_5m",
    "market_dataset_5m",
)


class MaintenanceCheckError(Exception):
    """Raised when a maintenance / data-quality check fails."""


def _fetch_one(database: Database, query: str, params: tuple[Any, ...] = ()) -> Any:
    connection = database.get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    finally:
        connection.close()


def _fetch_all(database: Database, query: str, params: tuple[Any, ...] = ()) -> list:
    connection = database.get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        connection.close()


def check_pipeline_runs(database: Database | None = None) -> str:
    """
    Verify the most recent bronze.pipeline_runs row has status='success'.

    Raises:
        MaintenanceCheckError: if no runs exist or the latest is not success.
    """
    db = database or Database()
    row = _fetch_one(
        db,
        """
        SELECT pipeline_run_id, status, dag_run_id, started_at
        FROM bronze.pipeline_runs
        ORDER BY started_at DESC NULLS LAST, pipeline_run_id DESC
        LIMIT 1
        """,
    )
    if row is None:
        raise MaintenanceCheckError("No rows found in bronze.pipeline_runs.")

    pipeline_run_id, status, dag_run_id, started_at = row
    status_value = status if isinstance(status, str) else str(status)
    logger.info(
        "Latest pipeline_run_id=%s status=%s dag_run_id=%s started_at=%s",
        pipeline_run_id,
        status_value,
        dag_run_id,
        started_at,
    )
    if status_value != "success":
        raise MaintenanceCheckError(
            f"Latest pipeline run {pipeline_run_id} has status={status_value!r}, "
            f"expected 'success' (dag_run_id={dag_run_id})."
        )
    return f"ok:pipeline_run_id={pipeline_run_id}"


def check_configured_symbols(database: Database | None = None) -> str:
    """
    Verify configured_symbols health:

    - every row has enabled=true
    - no row has bootstrap_status='failed'
    """
    db = database or Database()
    rows = _fetch_all(
        db,
        """
        SELECT symbol, enabled, bootstrap_status::text
        FROM bronze.configured_symbols
        ORDER BY symbol
        """,
    )
    if not rows:
        raise MaintenanceCheckError(
            "bronze.configured_symbols is empty; expected at least one symbol."
        )

    disabled = [r[0] for r in rows if not r[1]]
    failed = [r[0] for r in rows if r[2] == "failed"]

    logger.info(
        "configured_symbols count=%s disabled=%s failed=%s",
        len(rows),
        disabled,
        failed,
    )

    if disabled:
        raise MaintenanceCheckError(
            f"Symbols not enabled: {', '.join(disabled)}. All must have enabled=true."
        )
    if failed:
        raise MaintenanceCheckError(
            f"Symbols with bootstrap_status=failed: {', '.join(failed)}."
        )
    return f"ok:symbols={len(rows)}"


def check_bronze_freshness(
    database: Database | None = None,
    max_age: timedelta = BRONZE_FRESHNESS_MAX_AGE,
) -> str:
    """
    Verify bronze.binance_klines has recent data via MAX(open_time).

    Threshold: ``max_age`` (default 2 hours — see BRONZE_FRESHNESS_MAX_AGE).
    """
    db = database or Database()
    row = _fetch_one(db, "SELECT MAX(open_time) FROM bronze.binance_klines")
    max_open = row[0] if row else None
    if max_open is None:
        raise MaintenanceCheckError("bronze.binance_klines has no rows (MAX open_time is NULL).")

    if max_open.tzinfo is None:
        max_open = max_open.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    age = now - max_open
    logger.info(
        "bronze.binance_klines MAX(open_time)=%s age=%s threshold=%s",
        max_open,
        age,
        max_age,
    )
    if age > max_age:
        raise MaintenanceCheckError(
            f"Bronze klines are stale: MAX(open_time)={max_open.isoformat()} "
            f"(age={age}, threshold={max_age})."
        )
    return f"ok:max_open_time={max_open.isoformat()},age={age}"


def check_gold_tables(database: Database | None = None) -> str:
    """
    Verify 5m Gold feature-store tables each contain at least one row.
    """
    db = database or Database()
    counts: dict[str, int] = {}
    for table in GOLD_5M_TABLES:
        row = _fetch_one(db, f"SELECT COUNT(*) FROM gold.{table}")
        counts[table] = int(row[0]) if row else 0
        logger.info("gold.%s count=%s", table, counts[table])
        if counts[table] < 1:
            raise MaintenanceCheckError(
                f"gold.{table} is empty; expected at least one row."
            )
    return f"ok:counts={counts}"


def check_gold_consistency(database: Database | None = None) -> str:
    """
    Verify equal row counts across 5m Gold layers:

    indicators_5m == features_5m == signals_5m == dataset_5m
    """
    db = database or Database()
    counts: dict[str, int] = {}
    for table in GOLD_5M_TABLES:
        row = _fetch_one(db, f"SELECT COUNT(*) FROM gold.{table}")
        counts[table] = int(row[0]) if row else 0

    logger.info("Gold 5m consistency counts=%s", counts)
    values = list(counts.values())
    if len(set(values)) != 1:
        raise MaintenanceCheckError(
            "Gold 5m row-count mismatch: "
            + ", ".join(f"{k}={v}" for k, v in counts.items())
        )
    return f"ok:count={values[0]}"
