from __future__ import annotations

from src.clients.binance.client import BinanceClient
from src.common.database import Database
from src.config.settings import Settings
from src.extraction.binance_extractor import BinanceExtractor
from src.extraction.market_data_extractor import MarketDataExtractor
from src.loading.binance_loader import BinanceLoader
from src.monitoring.pipeline_monitor import PipelineMonitor
from src.quality.data_quality import DataQuality


class BronzePipeline:
    """Orchestrates extraction, validation, loading, and monitoring for Bronze."""

    def __init__(
        self,
        extractor: MarketDataExtractor | None = None,
    ) -> None:
        self._settings = Settings()
        self._database = Database(self._settings)
        self._client = BinanceClient()
        self._extractor: MarketDataExtractor = extractor or BinanceExtractor(
            self._settings,
            self._client,
        )
        self._data_quality = DataQuality()
        self._loader = BinanceLoader(self._database)
        self._monitor = PipelineMonitor(self._database)

    def run(self, dag_run_id: str) -> int:
        """Run the Bronze pipeline and return the total inserted rows."""
        pipeline_run_id: int | None = None

        try:
            pipeline_run_id = self._monitor.start_pipeline(dag_run_id)

            total_inserted_rows = 0

            current_prices = self._extractor.extract_current_price()
            self._data_quality.validate_current_prices(current_prices)
            total_inserted_rows += self._loader.insert_current_prices(
                current_prices,
                pipeline_run_id,
            )

            ticker_24h = self._extractor.extract_ticker_24h()
            self._data_quality.validate_ticker_24h(ticker_24h)
            total_inserted_rows += self._loader.insert_ticker_24h(
                ticker_24h,
                pipeline_run_id,
            )

            # Same behaviour as before: latest closed kline per symbol (limit=1, no dates).
            latest_klines = self._extractor.extract_klines(limit=1)
            self._data_quality.validate_latest_klines(latest_klines)
            total_inserted_rows += self._loader.insert_klines(
                latest_klines,
                pipeline_run_id,
            )

            self._monitor.finish_success(
                pipeline_run_id,
                rows_inserted=total_inserted_rows,
            )
            return total_inserted_rows
        except Exception as exc:
            if pipeline_run_id is not None:
                try:
                    self._monitor.finish_failure(pipeline_run_id, str(exc))
                except Exception:
                    pass
            raise
