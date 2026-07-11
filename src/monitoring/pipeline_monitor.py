from __future__ import annotations

from datetime import datetime, timezone

from src.common.database import Database
from src.common.logger import get_logger

logger = get_logger(__name__)


class PipelineMonitor:
    """Manages pipeline execution records in bronze.pipeline_runs."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def start_pipeline(self, dag_run_id: str) -> int:
        """Create a pipeline run record and return its identifier."""
        query = """
            INSERT INTO bronze.pipeline_runs (
                dag_run_id,
                started_at,
                status
            )
            VALUES (%s, %s, %s)
            RETURNING pipeline_run_id
        """
        connection = self._database.get_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (dag_run_id, datetime.now(timezone.utc), "running"),
                )
                pipeline_run_id = cursor.fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        if pipeline_run_id is None:
            raise RuntimeError("Failed to create pipeline run.")

        run_id = int(pipeline_run_id[0])
        logger.info(
            "Pipeline run started (dag_run_id=%s, pipeline_run_id=%s)",
            dag_run_id,
            run_id,
        )
        return run_id

    def finish_success(
        self,
        pipeline_run_id: int,
        rows_inserted: int,
        rows_updated: int = 0,
    ) -> None:
        """Mark a pipeline run as successful."""
        query = """
            UPDATE bronze.pipeline_runs
            SET finished_at = %s,
                status = %s,
                rows_inserted = %s,
                rows_updated = %s
            WHERE pipeline_run_id = %s
        """
        self._execute_update(
            query,
            (
                datetime.now(timezone.utc),
                "success",
                rows_inserted,
                rows_updated,
                pipeline_run_id,
            ),
        )
        logger.info(
            "Pipeline run succeeded (pipeline_run_id=%s, rows_inserted=%s, rows_updated=%s)",
            pipeline_run_id,
            rows_inserted,
            rows_updated,
        )

    def finish_failure(
        self,
        pipeline_run_id: int,
        error_message: str,
    ) -> None:
        """Mark a pipeline run as failed."""
        query = """
            UPDATE bronze.pipeline_runs
            SET finished_at = %s,
                status = %s,
                error_message = %s
            WHERE pipeline_run_id = %s
        """
        self._execute_update(
            query,
            (
                datetime.now(timezone.utc),
                "failed",
                error_message,
                pipeline_run_id,
            ),
        )
        logger.error(
            "Pipeline run failed (pipeline_run_id=%s, error=%s)",
            pipeline_run_id,
            error_message,
        )

    def _execute_update(self, query: str, params: tuple[object, ...]) -> None:
        connection = self._database.get_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
