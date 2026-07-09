from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.clients.binance.client import BinanceClient
from src.common.database import Database
from src.config.settings import Settings
from src.extraction.binance_extractor import (
    BINANCE_KLINES_MAX_LIMIT,
    BinanceExtractor,
)
from src.extraction.market_data_extractor import MarketDataExtractor
from src.loading.binance_loader import BinanceLoader
from src.monitoring.pipeline_monitor import PipelineMonitor
from src.quality.data_quality import DataQuality

EXCHANGE = "binance"

# Statuses that still need historical kline loading (including resume).
_ACTIVE_BOOTSTRAP_STATUSES = ("pending", "running", "failed")


class BootstrapPipeline:
    """
    Historical kline bootstrap for configured symbols.

    Loads only KLINES into bronze.binance_klines. Does not fetch price or 24h ticker.
    COMPLETED means historical load into Bronze finished successfully (independent of dbt/Airflow).
    """

    def __init__(
        self,
        extractor: MarketDataExtractor | None = None,
        settings: Settings | None = None,
        database: Database | None = None,
        loader: BinanceLoader | None = None,
        monitor: PipelineMonitor | None = None,
        data_quality: DataQuality | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._database = database or Database(self._settings)
        client = BinanceClient()
        self._extractor: MarketDataExtractor = extractor or BinanceExtractor(
            self._settings,
            client,
        )
        self._loader = loader or BinanceLoader(self._database)
        self._monitor = monitor or PipelineMonitor(self._database)
        self._data_quality = data_quality or DataQuality()

        source = self._settings.get_source(EXCHANGE)
        self._yaml_symbols: list[str] = list(source.get("symbols", []))
        historical = source.get("historical", {})
        self._default_history_days: int = int(historical.get("days", 365))
        self._interval: str = str(historical.get("interval", "1m"))

    def run(self, dag_run_id: str) -> int:
        """
        Run bootstrap for all YAML symbols that are not yet COMPLETED.

        Returns total kline rows submitted for insert across all symbols.
        """
        pipeline_run_id: int | None = None
        total_inserted = 0

        try:
            pipeline_run_id = self._monitor.start_pipeline(dag_run_id)
            self._sync_symbols_from_yaml()

            symbols = self._fetch_symbols_needing_bootstrap()
            for row in symbols:
                total_inserted += self._bootstrap_symbol(row, pipeline_run_id)

            self._monitor.finish_success(
                pipeline_run_id,
                rows_inserted=total_inserted,
            )
            return total_inserted
        except Exception as exc:
            if pipeline_run_id is not None:
                try:
                    self._monitor.finish_failure(pipeline_run_id, str(exc))
                except Exception:
                    pass
            raise

    def _sync_symbols_from_yaml(self) -> None:
        """Insert YAML symbols missing from configured_symbols as PENDING."""
        existing = {
            (r["exchange"], r["symbol"])
            for r in self._fetch_all_configured_symbols()
        }

        for symbol in self._yaml_symbols:
            key = (EXCHANGE, symbol)
            if key in existing:
                continue
            self._insert_configured_symbol(
                exchange=EXCHANGE,
                symbol=symbol,
                history_days=self._default_history_days,
            )

    def _bootstrap_symbol(
        self,
        row: dict[str, Any],
        pipeline_run_id: int,
    ) -> int:
        """Download historical klines for one symbol in blocks of max 1000."""
        symbol = row["symbol"]
        history_days = int(row["history_days"])
        inserted = 0

        try:
            self._mark_running(EXCHANGE, symbol)

            end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            start_ms = self._resolve_start_ms(row, history_days, end_ms)

            current_start = start_ms
            while current_start <= end_ms:
                # Binance hard-limit: at most BINANCE_KLINES_MAX_LIMIT candles per request.
                batch = self._extractor.extract_klines(
                    start_time=current_start,
                    end_time=end_ms,
                    limit=BINANCE_KLINES_MAX_LIMIT,
                    symbols=[symbol],
                )

                if not batch:
                    break

                self._data_quality.validate_latest_klines(batch)
                inserted += self._loader.insert_klines(batch, pipeline_run_id)

                last_open = max(int(k["open_time"]) for k in batch)
                last_open_dt = datetime.fromtimestamp(
                    last_open / 1000.0,
                    tz=timezone.utc,
                )
                self._update_last_bootstrap_open_time(
                    EXCHANGE,
                    symbol,
                    last_open_dt,
                )

                # Advance past the last candle (startTime is inclusive on Binance).
                current_start = last_open + 1

                if len(batch) < BINANCE_KLINES_MAX_LIMIT:
                    break

            self._mark_completed(EXCHANGE, symbol)
            return inserted
        except Exception as exc:
            self._mark_failed(EXCHANGE, symbol, str(exc))
            raise

    def _resolve_start_ms(
        self,
        row: dict[str, Any],
        history_days: int,
        end_ms: int,
    ) -> int:
        """Resume from last_bootstrap_open_time + 1ms, or history window start."""
        last = row.get("last_bootstrap_open_time")
        if last is not None:
            if isinstance(last, datetime):
                last_ms = int(last.timestamp() * 1000)
            else:
                last_ms = int(last)
            return last_ms + 1

        start_dt = datetime.now(timezone.utc) - timedelta(days=history_days)
        return int(start_dt.timestamp() * 1000)

    # ------------------------------------------------------------------
    # configured_symbols persistence
    # ------------------------------------------------------------------

    def _fetch_all_configured_symbols(self) -> list[dict[str, Any]]:
        query = """
            SELECT exchange, symbol, enabled, history_days, bootstrap_status,
                   last_bootstrap_open_time, bootstrap_started_at,
                   bootstrap_completed_at, last_incremental_at, last_error,
                   created_at, updated_at
            FROM bronze.configured_symbols
        """
        return self._fetch_all(query)

    def _fetch_symbols_needing_bootstrap(self) -> list[dict[str, Any]]:
        query = """
            SELECT exchange, symbol, enabled, history_days, bootstrap_status,
                   last_bootstrap_open_time, bootstrap_started_at,
                   bootstrap_completed_at, last_incremental_at, last_error,
                   created_at, updated_at
            FROM bronze.configured_symbols
            WHERE exchange = %s
              AND enabled = TRUE
              AND bootstrap_status::text = ANY(%s)
            ORDER BY symbol
        """
        return self._fetch_all(query, (EXCHANGE, list(_ACTIVE_BOOTSTRAP_STATUSES)))

    def _insert_configured_symbol(
        self,
        exchange: str,
        symbol: str,
        history_days: int,
    ) -> None:
        query = """
            INSERT INTO bronze.configured_symbols (
                exchange,
                symbol,
                enabled,
                history_days,
                bootstrap_status
            )
            VALUES (%s, %s, TRUE, %s, 'pending')
            ON CONFLICT (exchange, symbol) DO NOTHING
        """
        self._execute(query, (exchange, symbol, history_days))

    def _mark_running(self, exchange: str, symbol: str) -> None:
        query = """
            UPDATE bronze.configured_symbols
            SET bootstrap_status = 'running',
                bootstrap_started_at = COALESCE(bootstrap_started_at, %s),
                last_error = NULL,
                updated_at = %s
            WHERE exchange = %s AND symbol = %s
        """
        now = datetime.now(timezone.utc)
        self._execute(query, (now, now, exchange, symbol))

    def _mark_completed(self, exchange: str, symbol: str) -> None:
        query = """
            UPDATE bronze.configured_symbols
            SET bootstrap_status = 'completed',
                bootstrap_completed_at = %s,
                last_error = NULL,
                updated_at = %s
            WHERE exchange = %s AND symbol = %s
        """
        now = datetime.now(timezone.utc)
        self._execute(query, (now, now, exchange, symbol))

    def _mark_failed(self, exchange: str, symbol: str, error: str) -> None:
        query = """
            UPDATE bronze.configured_symbols
            SET bootstrap_status = 'failed',
                last_error = %s,
                updated_at = %s
            WHERE exchange = %s AND symbol = %s
        """
        now = datetime.now(timezone.utc)
        self._execute(query, (error[:4000], now, exchange, symbol))

    def _update_last_bootstrap_open_time(
        self,
        exchange: str,
        symbol: str,
        open_time: datetime,
    ) -> None:
        query = """
            UPDATE bronze.configured_symbols
            SET last_bootstrap_open_time = %s,
                updated_at = %s
            WHERE exchange = %s AND symbol = %s
        """
        now = datetime.now(timezone.utc)
        self._execute(query, (open_time, now, exchange, symbol))

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
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

    def _fetch_all(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        connection = self._database.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            connection.close()
