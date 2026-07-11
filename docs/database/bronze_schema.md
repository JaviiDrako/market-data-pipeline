# Bronze Layer Physical Schema

## Purpose

The Bronze layer is the entry point of the Data Warehouse.

Its responsibility is to persist raw market data received from external providers while applying only the minimum structural transformations required by the relational model.

No business calculations or analytical transformations are performed in this layer.

---

# Design Principles

The Bronze layer follows these principles:

- Immutable records
- Provider-specific tables
- Minimal transformation
- Historical preservation
- Full auditability
- High ingestion performance

---

# Current Tables

```
bronze/

├── pipeline_runs
├── configured_symbols
├── binance_klines
├── binance_price
└── binance_ticker_24h
```

---

# pipeline_runs

## Purpose

Stores metadata for every pipeline execution.

Each pipeline execution generates exactly one record.

Every Bronze record references the pipeline execution responsible for inserting it through `pipeline_run_id`.

---

## Stored Information

- DAG execution identifier
- Execution start time
- Execution finish time
- Pipeline status
- Inserted rows
- Updated rows
- Error message

---

# binance_klines

## Source Endpoint

```
GET /api/v3/klines
```

---

## Purpose

Stores OHLCV candlesticks returned by Binance.

Used by:

- **Incremental pipeline** — latest closed candle per symbol per run
- **Bootstrap pipeline** — historical ranges (up to 1000 candles per API request)

Each record represents one OHLCV candle as returned by Binance (no analytical transformations).

---

## Stored Information

- Symbol
- Open Time
- Close Time
- Open Price
- High Price
- Low Price
- Close Price
- Volume
- Quote Asset Volume
- Number of Trades
- Taker Buy Base Volume
- Taker Buy Quote Volume

---

# binance_price

## Source Endpoint

```
GET /api/v3/ticker/price
```

---

## Purpose

Stores the latest observed market price for each configured symbol.

---

## Stored Information

- Symbol
- Current Price

---

# binance_ticker_24h

## Source Endpoint

```
GET /api/v3/ticker/24hr
```

---

## Purpose

Stores rolling 24-hour market statistics provided directly by Binance.

No derived metrics are calculated locally.

---

## Stored Information

Examples include:

- Price Change
- Price Change Percentage
- Weighted Average Price
- High Price
- Low Price
- Volume
- Quote Volume
- Bid Price
- Ask Price
- Number of Trades

---

# Data Ingestion Flow

```
Binance REST API
        │
        ▼
Binance Client
        │
        ▼
Binance Extractor
        │
        ▼
Data Quality
        │
        ▼
Pipeline Monitor + Bronze Loader
        │
        ▼
Bronze Tables
```

Two orchestration entry points write into Bronze:

1. `BronzePipeline` — price + ticker + latest klines  
2. `BootstrapPipeline` — historical klines + `configured_symbols`

---

# configured_symbols

## Purpose

Operational control table for the **Bootstrap Pipeline** (historical kline load) and per-symbol lifecycle.

Tracks which symbols are enabled, how many days of history to load, bootstrap progress, and errors.

**No foreign keys** to market tables — intentionally decoupled.

---

## Columns

| Column | Description |
|--------|-------------|
| exchange | Provider key (e.g. `binance`) |
| symbol | Trading pair (e.g. `BTCUSDT`) |
| enabled | When false, bootstrap skips the symbol |
| history_days | How many days of history to download |
| bootstrap_status | `pending` → `running` → `completed` / `failed` |
| last_bootstrap_open_time | Last successfully loaded candle open time (resume cursor) |
| bootstrap_started_at | When bootstrap entered `running` |
| bootstrap_completed_at | When bootstrap reached `completed` |
| last_incremental_at | Reserved for future incremental tracking |
| last_error | Last error message when status is `failed` |
| created_at | Row creation time |
| updated_at | Last update time |

Primary key: `(exchange, symbol)`

---

## Bootstrap status values

- **pending** — symbol registered, history not loaded yet
- **running** — historical download in progress
- **completed** — full historical load into Bronze finished (independent of dbt/Airflow)
- **failed** — last attempt failed; `last_error` is set; re-run resumes from `last_bootstrap_open_time`

---

# Relationships

The Bronze layer maintains minimal relationships.

Each market table references the corresponding pipeline execution through `pipeline_run_id`, allowing complete traceability of every ingestion process.

No business relationships exist between market data tables.

`configured_symbols` has **no** foreign keys to other tables.

---

# Current Status

Implemented:

- Physical schema + PostgreSQL initialization (`docker/postgres/init/`)
- Binance extraction and Bronze loading
- Pipeline execution monitoring (`pipeline_runs`)
- `configured_symbols` operational table
- Historical bootstrap pipeline (Python)
- Airflow DAGs for incremental + bootstrap orchestration

Pending (product consumers, not Bronze schema):

- BI / Trading Bot / ML consumers of downstream layers