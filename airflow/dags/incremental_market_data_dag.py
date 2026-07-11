"""
Incremental Market Data DAG

Orchestrates the production incremental pipeline:

    BronzePipeline (extract → validate → load)
            ↓
       dbt build (staging → silver → gold)

Business logic lives in the Python pipelines and dbt models.
This DAG only schedules and invokes those components.

Schedule is derived from config.yaml via Settings:
    sources.binance.historical.interval  →  cron (interval_to_cron)
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator

# ---------------------------------------------------------------------------
# Project path (Airflow containers mount the repo at PROJECT_ROOT)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/opt/airflow/project"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.interval_cron import interval_to_cron  # noqa: E402
from src.common.logger import get_logger  # noqa: E402
from src.config.settings import Settings  # noqa: E402

logger = get_logger(__name__)

SOURCE_NAME = "binance"

# Resolve schedule at DAG parse time from config.yaml (via Settings only).
_settings = Settings()
_INTERVAL = _settings.get_history_interval(SOURCE_NAME)
SCHEDULE_CRON = interval_to_cron(_INTERVAL)

default_args = {
    "owner": "market-data",
    "depends_on_past": False,
    # One automatic retry for transient API / DB issues.
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
    "email_on_retry": False,
}


@dag(
    dag_id="incremental_market_data",
    description=(
        "Incremental market data pipeline: BronzePipeline then dbt build. "
        f"Schedule follows sources.{SOURCE_NAME}.historical.interval "
        f"({_INTERVAL} → cron {SCHEDULE_CRON!r})."
    ),
    doc_md=__doc__,
    default_args=default_args,
    schedule=SCHEDULE_CRON,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    # Avoid overlapping incremental runs (max one active at a time).
    max_active_runs=1,
    tags=["market-data", "incremental", "bronze", "dbt", SOURCE_NAME],
)
def incremental_market_data():
    """Define the incremental orchestration graph."""

    start = EmptyOperator(task_id="start")
    finish = EmptyOperator(task_id="finish")

    @task(task_id="run_bronze_pipeline")
    def run_bronze_pipeline(**context) -> int:
        """Execute the incremental BronzePipeline for the current DAG run."""
        from src.pipelines.bronze_pipeline import BronzePipeline

        dag_run = context["dag_run"]
        run_id = dag_run.run_id
        logger.info("Starting BronzePipeline for dag_run_id=%s", run_id)

        pipeline = BronzePipeline()
        rows = pipeline.run(run_id)

        logger.info(
            "BronzePipeline finished successfully: rows_inserted=%s dag_run_id=%s",
            rows,
            run_id,
        )
        return rows

    @task(task_id="run_dbt_build")
    def run_dbt_build() -> str:
        """
        Run full dbt build for the project.

        Uses project-level models graph (staging → silver → gold).
        Does not select individual models.
        """
        dbt_dir = PROJECT_ROOT / "dbt"
        profiles_dir = dbt_dir
        # Host-mounted dbt/logs and dbt/target are often not writable by
        # the airflow user; keep artifacts inside the container.
        log_path = Path(os.environ.get("DBT_LOG_PATH", "/tmp/dbt_logs"))
        target_path = Path(os.environ.get("DBT_TARGET_PATH", "/tmp/dbt_target"))
        log_path.mkdir(parents=True, exist_ok=True)
        target_path.mkdir(parents=True, exist_ok=True)

        cmd = [
            "dbt",
            "build",
            "--project-dir",
            str(dbt_dir),
            "--profiles-dir",
            str(profiles_dir),
            "--log-path",
            str(log_path),
            "--target-path",
            str(target_path),
        ]
        logger.info("Running dbt build: %s", " ".join(cmd))

        result = subprocess.run(
            cmd,
            cwd=str(dbt_dir),
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ},
        )

        if result.stdout:
            logger.info("dbt stdout (tail):\n%s", result.stdout[-4000:])
        if result.stderr:
            logger.warning("dbt stderr (tail):\n%s", result.stderr[-2000:])

        if result.returncode != 0:
            logger.error("dbt build failed with exit code %s", result.returncode)
            raise RuntimeError(
                f"dbt build failed with exit code {result.returncode}. "
                f"See task logs for details."
            )

        logger.info("dbt build completed successfully")
        return "ok"

    bronze = run_bronze_pipeline()
    dbt = run_dbt_build()

    start >> bronze >> dbt >> finish


incremental_market_data()
