"""
Bootstrap Market Data DAG

Orchestrates a **manual** historical load:

    BootstrapPipeline (historical klines → bronze)
            ↓
       dbt build (staging → silver → gold)

Business logic lives in ``BootstrapPipeline`` and dbt models.
This DAG only orchestrates those components.

Unlike the incremental DAG, this one has **no schedule**
(``schedule=None``) and is triggered only from the Airflow UI / CLI.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Project path (Airflow containers mount the repo at PROJECT_ROOT)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/opt/airflow/project"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    dag_id="bootstrap_market_data",
    description=(
        "Manual historical bootstrap: BootstrapPipeline then dbt build. "
        "No schedule — trigger only from the UI or CLI."
    ),
    doc_md=__doc__,
    default_args=default_args,
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    # Only one bootstrap run at a time (heavy historical load).
    max_active_runs=1,
    tags=["market-data", "bootstrap", "historical", "bronze", "dbt", "binance"],
)
def bootstrap_market_data():
    """Define the bootstrap orchestration graph."""

    start = EmptyOperator(task_id="start")
    finish = EmptyOperator(task_id="finish")

    @task(task_id="run_bootstrap_pipeline")
    def run_bootstrap_pipeline(**context) -> int:
        """Execute BootstrapPipeline for the current DAG run (historical klines only)."""
        from src.pipelines.bootstrap_pipeline import BootstrapPipeline

        dag_run = context["dag_run"]
        run_id = dag_run.run_id
        logger.info("Starting BootstrapPipeline for dag_run_id=%s", run_id)

        pipeline = BootstrapPipeline()
        rows = pipeline.run(run_id)

        logger.info(
            "BootstrapPipeline finished successfully: rows_submitted=%s dag_run_id=%s",
            rows,
            run_id,
        )
        return rows

    @task(task_id="run_dbt_build")
    def run_dbt_build() -> str:
        """
        Run full dbt build for the project.

        Same strategy as the incremental DAG: full project graph,
        writable log/target paths inside the container.
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

    bootstrap = run_bootstrap_pipeline()
    dbt = run_dbt_build()

    # dbt only runs if bootstrap succeeds (TaskFlow default dependency).
    start >> bootstrap >> dbt >> finish


bootstrap_market_data()
