# Market Data Pipeline

Production-oriented **ELT platform** for cryptocurrency market data.

The project ingests raw market data from Binance, persists it in a PostgreSQL Data Warehouse, transforms it with **dbt** under a **Medallion Architecture** (Bronze → Silver → Gold), and orchestrates execution with **Apache Airflow**.

It is designed as a clean data foundation for:

- **Power BI** analytics dashboards
- **Algorithmic trading** systems (pending)
- **Machine Learning** feature stores (pending)

> Consumers should read pre-computed Gold datasets. The pipeline prepares indicators, features and signals continuously so downstream systems do not recalculate market intelligence on demand.

---

## Table of contents

1. [Purpose](#purpose)
2. [Architecture overview](#architecture-overview)
3. [Medallion Architecture](#medallion-architecture)
4. [Business Intelligence](#business-intelligence)
5. [Technology stack](#technology-stack)
6. [Project structure](#project-structure)
7. [Current status](#current-status)
8. [Requirements](#requirements)
9. [Getting started (from zero)](#getting-started-from-zero)
10. [Configuration](#configuration)
11. [Logging](#logging)
12. [How to run the Bootstrap pipeline](#how-to-run-the-bootstrap-pipeline)
13. [How to run the Incremental pipeline](#how-to-run-the-incremental-pipeline)
14. [Airflow](#airflow)
15. [dbt](#dbt)
16. [PostgreSQL](#postgresql)
17. [Testing](#testing)
18. [CI / GitHub Actions](#ci--github-actions)
19. [Branching model](#branching-model)
20. [Documentation](#documentation)
21. [Roadmap](#roadmap)
22. [License](#license)

---

## Purpose

Build a maintainable, auditable and extensible market-data platform that:

1. Collects market data from exchange APIs (currently **Binance REST**).
2. Validates records before persistence (**Data Quality**).
3. Stores raw provider data in **Bronze**.
4. Normalizes and aggregates candles in **Silver** (1m + multi-timeframe).
5. Computes **Gold** technical indicators, trading features, signals and feature tables.
6. Tracks every pipeline execution (**Monitoring** / `pipeline_runs`).
7. Orchestrates scheduled incremental loads and manual historical bootstrap (**Airflow**).

---

## Architecture overview

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
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
     BronzePipeline                      BootstrapPipeline
     (incremental)                       (historical klines)
     price + ticker + latest 1m          full history (blocks of 1000)
              │                                   │
              └─────────────────┬─────────────────┘
                                ▼
                         Bronze Loader
                                │
                                ▼
                    PostgreSQL Warehouse
                    ┌───────────────────┐
                    │ bronze.*          │
                    │ configured_symbols│
                    │ pipeline_runs     │
                    └─────────┬─────────┘
                              │
                         dbt build
                              │
                    ┌─────────▼─────────┐
                    │ silver.*          │
                    │ staging views     │
                    │ market_candles*   │
                    │ market_snapshot   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ gold.*            │
                    │ indicators        │
                    │ features          │
                    │ signals           │
                    │ feature tables    │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         Power BI       Trading Bot    Machine Learning
        (implemented)      (pending)        (pending)
```

**Orchestration (Airflow)**

| DAG | Schedule | Responsibility |
|-----|----------|----------------|
| `incremental_market_data` | From `config.yaml` interval → cron | `BronzePipeline` → `dbt build` |
| `bootstrap_market_data` | Manual only | `BootstrapPipeline` → `dbt build` |

Business logic lives in `src/pipelines/` and `dbt/`. DAGs only schedule and invoke those components.

**Diagrams (Mermaid):** [`docs/diagrams/`](docs/diagrams/) — general architecture, incremental flow, bootstrap flow, medallion layers.

Full architecture documentation: [`docs/architecture/`](docs/architecture/).

---

## Medallion Architecture

| Layer | Schema | Role | Materialization |
|-------|--------|------|-----------------|
| **Bronze** | `bronze` | Raw provider data, audit, bootstrap control | Physical tables (SQL init) |
| **Silver** | `silver` | Staging views, canonical candles, multi-TF OHLCV, snapshots | dbt views + incremental MERGE |
| **Gold** | `gold` | Indicators → Features → Signals → Feature Tables | dbt incremental MERGE |

### Bronze (ingestion)

- `binance_klines`, `binance_price`, `binance_ticker_24h`
- `pipeline_runs` — execution audit
- `configured_symbols` — bootstrap state machine and resume cursor

### Silver (normalization & aggregation)

- Staging: `stg_binance_*` (views)
- Core: `market_candles` (1m), `market_snapshot`
- Aggregations: `market_candles_5m`, `_15m`, `_30m`, `_1h`, `_1d`

### Gold (intelligence)

```
Silver market_candles_* 
        → market_indicators_* 
        → market_features_* 
        → market_signals_* 
        → market_dataset_*   (final consumable tables)
```

Primary consumer tables: **`gold.market_dataset_*`** (keys + features + signals per timeframe).

---

## Business Intelligence

Power BI is the current analytics consumption layer for the Gold warehouse. The
versioned report combines `gold.market_dataset_bi` and
`gold.market_candles_bi` through a shared semantic model for executive,
technical, and cross-market analysis.

[![Executive Overview](bi/power-bi/screenshots/executive-overview.png)](bi/power-bi/README.md)

- [BI layer overview](bi/README.md)
- [Power BI project documentation](bi/power-bi/README.md)
- [View Interactive Power BI Report](https://app.powerbi.com/view?r=eyJrIjoiNjBlZTAwYWYtOGVmMC00N2NmLTkyYTEtODM2M2I1OTk1YWQ3IiwidCI6ImM1NWUwZDRlLTM4YmQtNDllZS1hZGE0LWIzYzQ1MWI0NWU2MyIsImMiOjR9)

---

## Technology stack

| Category | Technology |
|----------|------------|
| Language | Python 3.10+ |
| Warehouse | PostgreSQL 16 |
| Transformations | dbt-postgres |
| Orchestration | Apache Airflow 2.9 (LocalExecutor) |
| Containers | Docker & Docker Compose |
| HTTP client | `requests` + `tenacity` |
| DB driver | `psycopg` 3 |
| Config | YAML (`src/config/config.yaml`) via `Settings` |
| Source control | Git / GitHub |

---

## Project structure

```
market-data-pipeline/
├── airflow/
│   ├── dags/                      # Airflow DAGs (orchestration only)
│   ├── config/
│   └── plugins/
├── dbt/
│   ├── models/
│   │   ├── staging/binance/       # Bronze → staging views
│   │   ├── silver/                # Canonical + multi-TF candles
│   │   └── gold/                  # Indicators, features, signals, datasets
│   ├── macros/                    # Reusable SQL (aggregate, indicators, …)
│   ├── dbt_project.yml
│   └── profiles.yml
├── docker/
│   ├── .env.example               # Copy to docker/.env
│   ├── postgres/init/             # Warehouse + Bronze DDL
│   └── airflow/
├── bi/                            # Business Intelligence consumption layer
│   └── power-bi/                  # Versioned Power BI PBIP project
├── docs/                          # Architecture, database, ADRs, roadmap
├── src/
│   ├── clients/                   # Binance REST client
│   ├── common/                    # Database, logging, interval→cron
│   ├── config/                    # Settings + config.yaml
│   ├── extraction/                # Extractors
│   ├── loading/                   # Bronze loaders
│   ├── monitoring/                # pipeline_runs
│   ├── pipelines/                 # Bronze + Bootstrap orchestration
│   └── quality/                   # Pre-load validation
├── tests/
│   ├── unit/
│   └── integration/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Current status

| Component | Status |
|-----------|--------|
| Docker / PostgreSQL / Airflow infra | ✅ Implemented |
| Bronze schema + loading | ✅ Implemented |
| Binance client & extractor | ✅ Implemented |
| Data Quality (pre-Bronze) | ✅ Implemented |
| Pipeline monitoring (`pipeline_runs`) | ✅ Implemented |
| Bootstrap pipeline (historical klines) | ✅ Implemented |
| `configured_symbols` control table | ✅ Implemented |
| Settings-driven history (`days`, `interval`) | ✅ Implemented |
| Incremental Airflow DAG | ✅ Implemented |
| Bootstrap Airflow DAG | ✅ Implemented |
| dbt staging + Silver (1m + multi-TF) | ✅ Implemented |
| Gold indicators / features / signals / datasets | ✅ Implemented |
| Unit + integration tests | ✅ Implemented |
| Centralized Python logging (`get_logger`) | ✅ Implemented |
| GitHub Actions CI (unit + dbt parse) | ✅ Implemented |
| Mermaid architecture diagrams | ✅ Implemented |
| Power BI analytics dashboard | ✅ Implemented |
| Trading Bot | ⏳ Pending |
| Machine Learning pipelines | ⏳ Pending |
| Additional exchanges | ⏳ Pending |
| Maintenance DAG (daily checks) | ⏳ Not on mainline yet |

See [`docs/vision-and-roadmap.md`](docs/vision-and-roadmap.md) for the full roadmap.

---

## Requirements

### Software

- **Docker** and **Docker Compose** (recommended path)
- **Python 3.10+** (local CLI / tests)
- **Git**
- Network access to the **Binance public REST API**

### Host ports (defaults)

| Service | Port |
|---------|------|
| PostgreSQL (host → container) | `5433` → `5432` |
| Airflow Web UI | `8080` |

---

## Getting started (from zero)

### 1. Clone

```bash
git clone <repository-url>
cd market-data-pipeline   # or your local folder name
```

### 2. Environment file

```bash
cp docker/.env.example docker/.env
```

Edit `docker/.env` and set strong passwords. Required keys include:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `WAREHOUSE_DB` — analytical warehouse database name
- Airflow admin credentials
- `AIRFLOW__WEBSERVER__SECRET_KEY` (same value for webserver + scheduler)
- `AIRFLOW__CORE__FERNET_KEY`
- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Start Docker services

```bash
docker compose up -d
```

This starts:

- `market_data_postgres` — Postgres + init scripts (schemas `bronze`/`silver`/`gold`, Bronze DDL)
- `market_data_airflow_init` — DB migrate + admin user
- `market_data_airflow_webserver` — UI at http://localhost:8080
- `market_data_airflow_scheduler` — DAG scheduling

Wait until Postgres is healthy and Airflow init has finished.

### 4. Python virtualenv (host)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.
```

Host Python code reads warehouse credentials from `docker/.env` (see `src/common/database.py`). Default host connection: **localhost:5433**.

### 5. Align dbt credentials (local)

`dbt/profiles.yml` reads:

| Env var | Default (host) | Inside Airflow containers |
|---------|----------------|---------------------------|
| `DBT_HOST` | `localhost` | `postgres` |
| `DBT_PORT` | `5433` | `5432` |
| `DBT_USER` | `airflow` | set in compose |
| `DBT_PASSWORD` | `airflow` | set in compose |
| `DBT_DBNAME` | `market_data` | set in compose |

**Set `DBT_*` to match your `docker/.env` warehouse user/password/database** when running dbt from the host:

```bash
export DBT_HOST=localhost
export DBT_PORT=5433
export DBT_USER=<POSTGRES_USER from docker/.env>
export DBT_PASSWORD=<POSTGRES_PASSWORD from docker/.env>
export DBT_DBNAME=<WAREHOUSE_DB from docker/.env>
```

Airflow already injects `DBT_*` and `WAREHOUSE_*` for in-container runs.

### 6. Verify warehouse connectivity

```bash
source .venv/bin/activate
export PYTHONPATH=.
python -c "from src.common.database import Database; c=Database().get_connection(); print('OK', c.info.dbname); c.close()"
```

### 7. Recommended first load

1. Configure symbols and history in `src/config/config.yaml`.
2. Run **Bootstrap** (historical klines + dbt) — see [Bootstrap](#how-to-run-the-bootstrap-pipeline).
3. Enable / trigger **Incremental** for continuous updates — see [Incremental](#how-to-run-the-incremental-pipeline).

---

## Configuration

Single source of truth: **`src/config/config.yaml`**, loaded by `src.config.settings.Settings`.

Only settings that the project actually uses are present (no empty placeholder sections).

```yaml
sources:
  binance:
    symbols:
      - BTCUSDT
      - ETHUSDT
      - SOLUSDT
    historical:
      interval: 1m    # candle interval + incremental Airflow schedule
      days: 100       # bootstrap history depth
```

| Setting | Effect |
|---------|--------|
| `sources.binance.symbols` | Symbols extracted by Bronze + Bootstrap; synced into `bronze.configured_symbols` |
| `sources.binance.historical.days` | Bootstrap history depth (`Settings.get_history_days`) |
| `sources.binance.historical.interval` | Bootstrap/kline interval + incremental DAG cron (`Settings.get_pipeline_schedule`) |

Warehouse credentials come from `docker/.env` (and optional `WAREHOUSE_*` / `DBT_*` env vars), not from `config.yaml`.

Supported intervals for Airflow cron mapping: `1m`, `5m`, `15m`, `30m`, `1h`, `1d`.

> For faster local tests, temporarily set `days: 2`. Restore a larger value for production-like history.

---

## Logging

Python components use a shared helper:

```python
from src.common.logger import get_logger

logger = get_logger(__name__)
```

- Default level: `INFO` (override with env `LOG_LEVEL`)
- Integrates with **Airflow task logs** (no duplicate handlers when the root logger is already configured)
- Emits lifecycle events: pipeline start/finish, extraction counts, inserts, bootstrap symbol progress, validation summaries, errors

---

## How to run the Bootstrap pipeline

Loads **historical klines only** into `bronze.binance_klines` for configured symbols, with resume via `configured_symbols.last_bootstrap_open_time`. Then (in Airflow) runs full `dbt build`.

### Option A — Airflow (recommended)

```bash
docker exec market_data_airflow_scheduler \
  airflow dags unpause bootstrap_market_data

docker exec market_data_airflow_scheduler \
  airflow dags trigger bootstrap_market_data
```

Or use the UI: http://localhost:8080 → `bootstrap_market_data` → Trigger.

### Option B — Python (Bronze history only, no dbt)

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

Then run dbt separately if needed:

```bash
cd dbt && dbt build --profiles-dir .
```

### Check bootstrap status

```sql
SELECT exchange, symbol, bootstrap_status, last_bootstrap_open_time, last_error
FROM bronze.configured_symbols
ORDER BY symbol;
```

Details: [`docs/architecture/bootstrap_pipeline.md`](docs/architecture/bootstrap_pipeline.md).

---

## How to run the Incremental pipeline

Loads **latest** price, 24h ticker and 1m kline per symbol (`BronzePipeline`), then `dbt build` (staging → silver → gold).

### Option A — Airflow (recommended)

Schedule is derived from `sources.binance.historical.interval` (e.g. `1m` → every minute).

```bash
docker exec market_data_airflow_scheduler \
  airflow dags unpause incremental_market_data

# Optional manual trigger
docker exec market_data_airflow_scheduler \
  airflow dags trigger incremental_market_data
```

### Option B — Python + dbt

```bash
source .venv/bin/activate
export PYTHONPATH=.

python -c "
from datetime import datetime, timezone
from src.pipelines.bronze_pipeline import BronzePipeline

run_id = 'manual_incremental_' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
rows = BronzePipeline().run(run_id)
print(f'Bronze finished. Rows inserted: {rows}')
"

cd dbt && dbt build --profiles-dir .
```

---

## Airflow

| Item | Value |
|------|-------|
| UI | http://localhost:8080 |
| Executor | LocalExecutor |
| DAGs | `airflow/dags/*.py` |
| Project mount | `/opt/airflow/project` (`PROJECT_ROOT`) |

Both production DAGs:

1. Run the corresponding Python pipeline with `dag_run_id`.
2. On success, run `dbt build` against the warehouse.

See [`docs/architecture/airflow_architecture.md`](docs/architecture/airflow_architecture.md).

---

## dbt

```bash
cd dbt
dbt debug --profiles-dir .
dbt build --profiles-dir .
dbt test --profiles-dir .
```

Useful selects:

```bash
dbt run --select staging
dbt run --select silver
dbt run --select gold
dbt test --select gold
```

Models are organized by Medallion layer under `dbt/models/`. Macros live under `dbt/macros/` (single implementation per indicator/feature/signal/aggregation).

---

## PostgreSQL

| Item | Default / notes |
|------|-----------------|
| Container | `market_data_postgres` |
| Host port | `5433` |
| Warehouse DB | `WAREHOUSE_DB` from `docker/.env` |
| Schemas | `bronze`, `silver`, `gold` |
| Init | `docker/postgres/init/` |

Connect example (replace credentials):

```bash
psql -h localhost -p 5433 -U <POSTGRES_USER> -d <WAREHOUSE_DB>
```

Bronze DDL is applied on first volume init only. Recreate volumes if you need a clean schema bootstrap:

```bash
docker compose down -v   # destructive: deletes data
docker compose up -d
```

---

## Testing

From the project root with venv active and `PYTHONPATH=.`:

### Unit tests

```bash
python -m unittest discover -s tests/unit -v
```

Covers extractor behaviour, bootstrap helpers, interval→cron mapping, etc.

### Integration tests

Require a running warehouse (`docker compose up -d`) and network access to Binance where applicable.

```bash
python -m unittest discover -s tests/integration -v
```

Notable tests:

| Test | Purpose |
|------|---------|
| `test_pipeline_end_to_end.py` | Bronze → dbt Silver/Gold multi-timeframe path |
| `test_bootstrap_pipeline.py` | Historical bootstrap behaviour |
| `test_aggregation_5m.py` | Deterministic 1m → 5m OHLCV aggregation |

> Some E2E paths assume a clean or controlled warehouse state for multi-timeframe completeness checks.

---

## CI / GitHub Actions

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

Runs on **push** and **pull_request** (fast path — no full Docker integration):

1. Checkout
2. Setup Python 3.11
3. Install `requirements.txt`
4. Validate critical imports
5. **Unit tests** (`tests/unit`)
6. **dbt parse** (project/manifest validation; no live warehouse required)

```bash
# Local equivalents
export PYTHONPATH=.
python -m unittest discover -s tests/unit -v
cd dbt && dbt parse --profiles-dir .
```

---

## Branching model

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases / protected baseline |
| `develop` | Integration branch for completed sprints |
| `feature/*` | Short-lived feature branches |

Examples of historical feature branches: `feature/bronze-pipeline`, `feature/silver-aggregations`, `feature/gold-indicators`, `feature/airflow-incremental`, `feature/final-testing`, `feature/project-documentation`.

Workflow used in this project:

1. Branch from `develop`.
2. Small, focused commits.
3. Merge into `develop` when the sprint is complete.
4. No force-push to shared branches; documentation sprints do not change business logic.

---

## Documentation

| Path | Content |
|------|---------|
| [`bi/README.md`](bi/README.md) | Business Intelligence layer overview |
| [`bi/power-bi/README.md`](bi/power-bi/README.md) | Power BI dashboard, semantic model and report pages |
| [`docs/README.md`](docs/README.md) | Full documentation index |
| [`docs/architecture/`](docs/architecture/) | System, Airflow, Bootstrap, Warehouse, Data Quality, future improvements |
| [`docs/diagrams/`](docs/diagrams/) | Mermaid diagrams (architecture, flows, medallion) |
| [`docs/database/`](docs/database/) | Bronze / Silver / Gold schemas |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`docs/vision-and-roadmap.md`](docs/vision-and-roadmap.md) | Vision + remaining work |

---

## Roadmap

### Implemented (this repository)

- Full Bronze incremental ELT path
- Historical Bootstrap with resume + `configured_symbols`
- Silver multi-timeframe aggregations
- Gold indicators, features, signals, feature tables
- Airflow incremental + bootstrap DAGs
- Pre-load Data Quality and pipeline monitoring
- Unit and integration test suites
- Centralized logging and GitHub Actions CI
- Mermaid architecture diagrams
- Power BI analytics dashboard backed by Gold BI consumption views

### Pending (not implemented — do not treat as available)

| Area | Status |
|------|--------|
| **Additional BI implementations** (Evidence, Rill, Tableau, …) | Future |
| **Trading Bot** | Pending |
| **Machine Learning** | Pending |
| Additional data providers (Yahoo, Coinbase, …) | Pending |
| Daily maintenance / ops DAG on mainline | Pending |
| Advanced DQ metrics & reporting dashboards | Pending |

Details: [`docs/vision-and-roadmap.md`](docs/vision-and-roadmap.md).

---

## License

This project is intended for **educational purposes and portfolio development**.
