# System Architecture Overview

## Purpose

The Market Data Pipeline is a production-oriented ELT platform that ingests, validates, transforms and serves cryptocurrency market data.

Every component has a single responsibility. Raw market data is collected from external providers, stored in a PostgreSQL Data Warehouse, transformed with dbt under a Medallion layout, and prepared for future BI, trading and ML consumers.

The design supports additional market data providers without major architectural rewrites.

---

# High-Level Architecture

```
                    External Market Data Providers
                               │
             ┌─────────────────┴─────────────────┐
             │                                   │
         Binance API                      Future Providers
                                              (pending)
             │
             ▼
      Market Data Client
             │
             ▼
     Market Data Extractor
             │
             ▼
        Data Quality
             │
     ┌───────┴────────┐
     ▼                ▼
 BronzePipeline   BootstrapPipeline
 (incremental)    (historical klines)
     │                │
     └───────┬────────┘
             ▼
        Bronze Loader + Pipeline Monitor
             │
             ▼
     PostgreSQL Warehouse (bronze.*)
             │
        Airflow DAGs
     (schedule / trigger)
             │
             ▼
          dbt build
             │
     ┌───────┴────────┐
     ▼                ▼
 Silver            Gold
 (staging,         (indicators →
  candles,          features →
  multi-TF)         signals →
                    feature tables)
             │
     ┌───────┼───────────────┐
     ▼       ▼               ▼
    BI   Trading Bot        ML
 (pending) (pending)     (pending)
```

---

# Component Responsibilities

## Market Data Providers

External APIs providing market information.

**Current:** Binance REST API

**Pending:** Yahoo Finance, Coinbase, Kraken, Polygon, etc.

---

## Client Layer (`src/clients/`)

Communicates with external providers.

- Build HTTP requests
- Execute REST calls with retries (`tenacity`)
- Handle network errors
- Return raw JSON

Clients do not transform or persist data.

---

## Extraction Layer (`src/extraction/`)

Maps provider JSON into standardized Python dictionaries.

- Read symbols from `Settings` / `config.yaml`
- Request market data per symbol
- Expose a shared `MarketDataExtractor` contract

Used by both **Bronze** (latest) and **Bootstrap** (historical range) pipelines.

---

## Data Quality Layer (`src/quality/`)

Fail-fast structural validation **before** Bronze insert.

See [data_quality.md](data_quality.md).

---

## Loading Layer (`src/loading/`)

Persists validated records into Bronze tables.

- Insert with idempotent conflict handling where applicable (`ON CONFLICT DO NOTHING` for klines)
- Associate rows with `pipeline_run_id`
- Return real inserted row counts

---

## Monitoring (`src/monitoring/`)

Records pipeline executions in `bronze.pipeline_runs`:

- `dag_run_id`, start/finish timestamps
- status (`running` / `success` / `failed`)
- rows inserted / updated
- error message on failure

---

## Pipelines (`src/pipelines/`)

| Pipeline | Class | Role |
|----------|-------|------|
| Incremental Bronze | `BronzePipeline` | Latest price + ticker + 1m kline → Bronze |
| Historical Bootstrap | `BootstrapPipeline` | Full kline history → Bronze + `configured_symbols` state |

Neither pipeline runs dbt. Orchestration layers (Airflow or manual CLI) invoke `dbt build` after a successful pipeline run.

---

## Bronze Layer

Raw, provider-specific, auditable storage. See [warehouse_architecture.md](warehouse_architecture.md) and [../database/bronze_schema.md](../database/bronze_schema.md).

---

## Silver Layer

Standardized, provider-independent models and multi-timeframe aggregations. See [../database/silver_schema.md](../database/silver_schema.md).

---

## Gold Layer

Persisted analytical intelligence: indicators, features, signals, feature tables. See [../database/gold_schema.md](../database/gold_schema.md).

---

## Orchestration (Airflow)

DAGs under `airflow/dags/` schedule or trigger pipelines and `dbt build`.

| DAG | Schedule |
|-----|----------|
| `incremental_market_data` | From `config.yaml` interval → cron |
| `bootstrap_market_data` | Manual only |

See [airflow_architecture.md](airflow_architecture.md).

---

# Configuration

Behaviour is configuration-driven via `src/config/config.yaml` and `Settings`:

| Method | Source key | Used by |
|--------|------------|---------|
| `get_symbols(source)` | `sources.<source>.symbols` | Extractors, bootstrap sync |
| `get_history_days(source)` | `sources.<source>.historical.days` | Bootstrap depth |
| `get_history_interval(source)` | `sources.<source>.historical.interval` | Kline interval |
| `get_pipeline_schedule(source)` | same interval → cron | Incremental Airflow DAG |

Database connection defaults come from `docker/.env` and optional `WAREHOUSE_HOST` / `WAREHOUSE_PORT` overrides (Airflow network).

---

# Incremental vs Bootstrap

| | Incremental | Bootstrap |
|--|-------------|-----------|
| Entry point | `BronzePipeline` | `BootstrapPipeline` |
| Price / 24h ticker | Yes | No |
| Klines | Latest closed candle (`limit=1`) | History in blocks of 1000 |
| Control table | — | `configured_symbols` |
| Typical trigger | Scheduled Airflow DAG | Manual Airflow / CLI once per env |
| Then | `dbt build` | `dbt build` |

Both write klines to the same `bronze.binance_klines` table.

---

# Current Implementation Status

**Implemented**

- Docker infrastructure (Postgres + Airflow)
- PostgreSQL warehouse + Bronze DDL
- Binance client & extractor
- Data Quality + Bronze Loader + Pipeline Monitor
- Bronze incremental pipeline
- Bootstrap historical pipeline + `configured_symbols`
- Settings-driven symbols / history / schedule
- dbt staging, Silver (incl. multi-TF), Gold (indicators → datasets)
- Airflow incremental + bootstrap DAGs
- Unit and integration tests

**Pending (not in this repository as product features)**

- BI dashboards
- Trading bot
- Machine Learning pipelines
- Additional providers
- Mainline maintenance / ops DAG

---

# Design Principles

- Single Responsibility Principle
- Separation of Concerns (orchestration ≠ business logic)
- Configuration over hardcoding
- Extensibility for new providers
- Medallion Architecture
- Fail-fast data quality before persistence
- Incremental processing in dbt (MERGE on natural keys)

---

# Diagrams

Mermaid diagrams (GitHub-renderable):

| Diagram | Path |
|---------|------|
| General architecture | [../diagrams/architecture_overview.md](../diagrams/architecture_overview.md) |
| Incremental flow | [../diagrams/incremental_flow.md](../diagrams/incremental_flow.md) |
| Bootstrap flow | [../diagrams/bootstrap_flow.md](../diagrams/bootstrap_flow.md) |
| Medallion layers | [../diagrams/medallion_architecture.md](../diagrams/medallion_architecture.md) |

---

# Future Improvements

The following items are **conscious design deferrals**, not forgotten work.
They should be revisited when volume, symbol count, or operational needs justify the complexity.

| Area | Future improvement | Why it is deferred today |
|------|--------------------|--------------------------|
| **dbt orchestration** | Optimize `dbt build` via **partial model selection** (e.g. Bronze-adjacent Silver on every tick; Gold on a slower cadence or selective `--select`) | Full graph builds keep the pipeline simple and correct for a small symbol set. Partial selection adds scheduling and dependency policy that is unnecessary until build time becomes a bottleneck. |
| **Airflow concurrency** | Revisit `max_active_runs` (and optionally pools/parallelism) when the **number of symbols grows significantly** | `max_active_runs=1` avoids overlapping MERGE/load races and is the right default for demo and low-cardinality production. Higher concurrency only pays off with careful isolation and rate-limit budgets. |
| **Bronze bulk load** | Optimize kline inserts with **batch insert / PostgreSQL `COPY`** if historical volume requires it | Per-row insert with accurate `ON CONFLICT` rowcounts prioritizes correctness and resume metrics. Batch/COPY is a measured optimization once bootstrap backfills dominate runtime. |

Related operational themes (also future, not blocking BI work):

- Richer freshness monitoring and alerting
- Stronger dbt uniqueness / contract tests
- CI expansion beyond unit tests + `dbt parse` (e.g. scheduled integration)

When implementing any row above, prefer incremental changes that preserve Medallion boundaries and thin Airflow DAGs.
