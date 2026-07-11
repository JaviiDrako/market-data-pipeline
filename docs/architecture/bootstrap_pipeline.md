# Bootstrap Pipeline – Historical Kline Load

## Purpose

The Bootstrap Pipeline performs a **one-time (or resumable) historical load of klines** into Bronze for every configured trading symbol.

It is independent of the incremental Bronze path (price / ticker / latest candle).

`bootstrap_status = completed` means: historical klines for that symbol are fully present in `bronze.binance_klines` for the configured history depth.

After a successful bootstrap run, **Airflow** (or a manual operator) typically runs `dbt build` so Silver/Gold catch up. dbt is **not** embedded inside `BootstrapPipeline` itself.

---

## Scope

| Included | Excluded |
|----------|----------|
| Klines (OHLCV) only | Current price |
| `bronze.binance_klines` | 24h ticker |
| Symbol control via `bronze.configured_symbols` | Trading decisions |
| Resume from last progress | Automatic schedule (manual / intentional trigger) |
| History depth from `Settings` / `config.yaml` | Business indicators (Gold) |

---

## Architecture

```
config.yaml (symbols + historical.days / interval)
        │
        ▼
Settings.get_symbols / get_history_days / get_history_interval
        │
        ▼
BootstrapPipeline
        │
        ├── sync → bronze.configured_symbols (insert new as PENDING)
        │
        ├── for each enabled symbol not COMPLETED:
        │         PENDING / FAILED / RUNNING
        │              │
        │              ▼ RUNNING
        │         MarketDataExtractor.extract_klines(
        │             start_time, end_time, limit=1000
        │         )
        │              │  (blocks of max 1000 — Binance API limit)
        │              ▼
        │         Data Quality → BinanceLoader → bronze.binance_klines
        │              │
        │              ▼ update last_bootstrap_open_time
        │              │
        │              ▼ COMPLETED (or FAILED + last_error)
        │
        └── pipeline_runs monitoring
```

Bronze **incremental** pipeline continues to load latest candles only (`extract_klines(limit=1)`).

Both pipelines use the same `MarketDataExtractor` interface.

---

## Configuration (Settings / config.yaml)

```yaml
sources:
  binance:
    symbols:
      - BTCUSDT
      - ETHUSDT
      - SOLUSDT
    historical:
      interval: 1m    # kline interval
      days: 100       # history depth for bootstrap
```

| Settings API | Meaning |
|--------------|---------|
| `get_symbols("binance")` | Symbols to sync into `configured_symbols` |
| `get_history_days("binance")` | Depth in days |
| `get_history_interval("binance")` | Candle interval string |

No bootstrap depth is hard-coded in the pipeline class beyond defaults inside `Settings.get_historical`.

---

## Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `MarketDataExtractor` | Shared extract contract |
| `BinanceExtractor.extract_klines` | Single reusable kline extract (optional date range) |
| `BootstrapPipeline` | Symbol sync, status machine, pagination, resume |
| `DataQuality` | Validate each batch before load |
| `BinanceLoader` | Persist klines (`ON CONFLICT DO NOTHING`) |
| `configured_symbols` | Per-symbol bootstrap state and progress |
| `PipelineMonitor` | `pipeline_runs` audit row |

---

## Historical download flow

Binance `GET /api/v3/klines` returns **at most 1000 candles per request** (`BINANCE_KLINES_MAX_LIMIT`).

```
current_start
    ↓
request (limit = 1000)
    ↓
validate + insert bronze.binance_klines
    ↓
last_bootstrap_open_time = max(open_time)
    ↓
current_start = last_open_time_ms + 1
    ↓
repeat until empty batch or partial block (< 1000)
```

---

## Resume behaviour

After each successful block insert, `last_bootstrap_open_time` is updated.

If the process crashes or marks `failed`:

1. Next run loads the same symbol again (`failed` / `running` / `pending`).
2. Start time becomes `last_bootstrap_open_time + 1 ms`.
3. Already loaded candles are not re-downloaded from the beginning.
4. Duplicate PKs are ignored via PostgreSQL `ON CONFLICT (symbol, open_time) DO NOTHING`.

---

## Status machine

```
YAML new symbol
      ↓
   PENDING
      ↓
   RUNNING  ← bootstrap starts
      ↓
  COMPLETED  (success)
   or
   FAILED    (exception; last_error set; resume later)
```

---

## How to add new symbols

1. Edit `src/config/config.yaml` and add the symbol under `sources.binance.symbols`.
2. Run the Bootstrap Pipeline (Airflow DAG or Python).
3. The pipeline inserts the symbol as `pending` with `history_days` from YAML and downloads history until `completed`.

No manual SQL is required for normal operation.

---

## How to run

### Airflow (recommended — includes dbt)

```bash
docker exec market_data_airflow_scheduler \
  airflow dags unpause bootstrap_market_data

docker exec market_data_airflow_scheduler \
  airflow dags trigger bootstrap_market_data
```

UI: http://localhost:8080 → `bootstrap_market_data` → Trigger.

DAG details: [airflow_architecture.md](airflow_architecture.md).

### Python only (Bronze history; run dbt separately)

```bash
source .venv/bin/activate
export PYTHONPATH=.

python -c "
from datetime import datetime, timezone
from src.pipelines.bootstrap_pipeline import BootstrapPipeline

run_id = 'manual_bootstrap_' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
rows = BootstrapPipeline().run(run_id)
print(f'Bootstrap finished. Rows submitted: {rows}')
"
```

### Check status

```sql
SELECT exchange, symbol, bootstrap_status, last_bootstrap_open_time, last_error
FROM bronze.configured_symbols
ORDER BY symbol;
```

---

## Relation to Bronze incremental pipeline

| | Bronze (incremental) | Bootstrap |
|--|----------------------|-----------|
| Entry | `BronzePipeline` | `BootstrapPipeline` |
| Klines | Latest only (`limit=1`) | Full history (blocks of 1000) |
| Price / Ticker | Yes | No |
| Typical schedule | Airflow cron from `interval` | Manual / intentional |
| Airflow DAG | `incremental_market_data` | `bootstrap_market_data` |

Both write to the same `bronze.binance_klines` table.
