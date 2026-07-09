# Bootstrap Pipeline – Historical Kline Load

## Purpose

The Bootstrap Pipeline performs a **one-time (or resumable) historical load of klines** into Bronze for every configured trading symbol.

It is independent of:

- Airflow DAGs (orchestration comes in a later sprint)
- dbt (Silver/Gold transformations are not part of bootstrap completion)

`bootstrap_status = completed` means: historical klines for that symbol are fully present in `bronze.binance_klines`.

---

## Scope

| Included | Excluded |
|----------|----------|
| Klines (OHLCV) only | Current price |
| `bronze.binance_klines` | 24h ticker |
| Symbol control via `bronze.configured_symbols` | Automatic dbt runs |
| Resume from last progress | Trading decisions |

---

## Architecture

```
config.yaml (symbols + history days)
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
        │         BinanceLoader → bronze.binance_klines
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

## Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `MarketDataExtractor` | Shared extract contract |
| `BinanceExtractor.extract_klines` | Single reusable kline extract (with optional date range) |
| `BootstrapPipeline` | Symbol sync, status machine, pagination, resume |
| `BinanceLoader` | Persist klines into Bronze (`ON CONFLICT DO NOTHING`) |
| `configured_symbols` | Per-symbol bootstrap state and progress |

---

## Historical download flow

Binance `GET /api/v3/klines` returns **at most 1000 candles per request** (`BINANCE_KLINES_MAX_LIMIT`).

The bootstrap **never** assumes a single request returns the full history.

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

1. Next run loads the same symbol again (status `failed` / `running` / `pending`).
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
      ↓
   FAILED    (exception; last_error set; resume later)
```

---

## How to add new symbols

1. Edit `src/config/config.yaml`:

```yaml
sources:
  binance:
    symbols:
      - BTCUSDT
      - ETHUSDT
      - SOLUSDT
      - NEWUSDT   # add here
    historical:
      interval: 1m
      days: 365
```

2. Run the Bootstrap Pipeline (see below).

3. The pipeline will:

   - Detect `NEWUSDT` is missing from `configured_symbols`
   - Insert it as `pending` with `history_days` from YAML
   - Download history and mark `completed`

No manual SQL is required for normal operation.

---

## How to run the Bootstrap Pipeline manually

Prerequisites:

- Docker stack up (`docker compose up -d`)
- Warehouse reachable (default `localhost:5433`)
- Project venv with dependencies installed

From the project root:

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

Check status:

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
| Typical schedule | Frequent (Airflow later) | Once per symbol (or resume) |

Both write to the same `bronze.binance_klines` table.
