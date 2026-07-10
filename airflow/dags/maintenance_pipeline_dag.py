"""
Maintenance / Data Quality DAG

Daily health checks for the market data warehouse. This DAG does **not**:

- extract market data
- run BronzePipeline or BootstrapPipeline
- run dbt

It only validates system state via reusable checks in
``src.quality.maintenance_checks``.

Schedule: once per day (UTC midnight).
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/opt/airflow/project"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

default_args = {
    "owner": "market-data",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
    "email_on_retry": False,
}


@dag(
    dag_id="maintenance_pipeline",
    description=(
        "Daily maintenance and data-quality checks for Bronze / Gold state. "
        "No extraction, no pipelines, no dbt."
    ),
    doc_md=__doc__,
    default_args=default_args,
    # Once per day at 00:00 UTC.
    schedule="0 0 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["market-data", "maintenance", "data-quality"],
)
def maintenance_pipeline():
    """Define the maintenance validation graph."""

    start = EmptyOperator(task_id="start")
    finish = EmptyOperator(task_id="finish")

    @task(task_id="check_pipeline_runs")
    def check_pipeline_runs() -> str:
        from src.quality.maintenance_checks import check_pipeline_runs as _check

        logger.info("Running check_pipeline_runs")
        result = _check()
        logger.info("check_pipeline_runs: %s", result)
        return result

    @task(task_id="check_configured_symbols")
    def check_configured_symbols() -> str:
        from src.quality.maintenance_checks import check_configured_symbols as _check

        logger.info("Running check_configured_symbols")
        result = _check()
        logger.info("check_configured_symbols: %s", result)
        return result

    @task(task_id="check_bronze_freshness")
    def check_bronze_freshness() -> str:
        from src.quality.maintenance_checks import check_bronze_freshness as _check

        logger.info("Running check_bronze_freshness")
        result = _check()
        logger.info("check_bronze_freshness: %s", result)
        return result

    @task(task_id="check_gold_tables")
    def check_gold_tables() -> str:
        from src.quality.maintenance_checks import check_gold_tables as _check

        logger.info("Running check_gold_tables")
        result = _check()
        logger.info("check_gold_tables: %s", result)
        return result

    @task(task_id="check_gold_consistency")
    def check_gold_consistency() -> str:
        from src.quality.maintenance_checks import check_gold_consistency as _check

        logger.info("Running check_gold_consistency")
        result = _check()
        logger.info("check_gold_consistency: %s", result)
        return result

    t_pipeline = check_pipeline_runs()
    t_symbols = check_configured_symbols()
    t_freshness = check_bronze_freshness()
    t_gold = check_gold_tables()
    t_consistency = check_gold_consistency()

    start >> t_pipeline >> t_symbols >> t_freshness >> t_gold >> t_consistency >> finish


maintenance_pipeline()
