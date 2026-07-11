# Data Warehouse Architecture

## Purpose

The project uses a **PostgreSQL** Data Warehouse to centralize market data collected from cryptocurrency exchanges.

Analytical applications and future trading / ML systems should query the warehouse rather than external APIs directly.

This provides:

- Historical persistence
- Better query performance
- Data consistency
- Reproducible analytics
- Support for multiple consumers

---

# Why a Data Warehouse?

A warehouse separates operational collection from analytical consumption.

Data is collected once and reused by:

- BI dashboards (**pending**)
- Trading algorithms (**pending**)
- Machine learning models (**pending**)
- Ad-hoc SQL analysis (**available today**)

---

# Medallion Architecture

```
Bronze  (raw, provider-specific)
   │
   ▼
Silver  (normalized + multi-timeframe candles)
   │
   ▼
Gold    (indicators → features → signals → feature tables)
```

Each layer increases business value and readiness for consumption.

---

# Bronze Layer

**Purpose:** store raw provider data with minimal transformation.

Characteristics:

- Immutable inserts (idempotent where needed)
- Auditable via `pipeline_run_id`
- Provider-specific table shapes
- Historical preservation

Tables (Binance):

- `bronze.binance_klines`
- `bronze.binance_price`
- `bronze.binance_ticker_24h`
- `bronze.pipeline_runs`
- `bronze.configured_symbols`

Only structural mapping is performed. No business indicators.

Details: [../database/bronze_schema.md](../database/bronze_schema.md).

---

# Silver Layer

**Purpose:** standardize and aggregate for analytics.

Responsibilities:

- Staging views over Bronze
- Provider-independent column names
- Canonical 1-minute candles
- Multi-timeframe OHLCV aggregations (5m, 15m, 30m, 1h, 1d)
- Market snapshots

Details: [../database/silver_schema.md](../database/silver_schema.md).

---

# Gold Layer

**Purpose:** persist intelligence datasets ready for consumers.

```
Silver candles_*
      → Indicators
      → Features
      → Signals
      → Feature Tables (market_dataset_*)
```

Gold prioritizes query performance and consumer readiness over pure normalization.

Details: [../database/gold_schema.md](../database/gold_schema.md).

---

# Why Bronze Tables Are Provider-Specific

Bronze stores responses as close as possible to the original API:

```
bronze.binance_klines
# future: bronze.yahoo_ohlc, …
```

Different providers expose different fields. Normalization happens in Silver, minimizing data loss and simplifying future integrations.

ADR: [../adr/adr_003_provider-specific_bronze_tables.md](../adr/adr_003_provider-specific_bronze_tables.md).

---

# Data Flow

```
Binance API
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
Bronze Loader (+ Pipeline Monitor)
      │
      ▼
Bronze Tables
      │
      ▼
dbt (staging views)
      │
      ▼
Silver (candles, multi-TF, snapshot)
      │
      ▼
Gold (indicators → features → signals → datasets)
```

Two ingestion entry points feed Bronze:

1. **Incremental** — latest market state every schedule tick  
2. **Bootstrap** — historical klines until `configured_symbols` is `completed`

---

# Why dbt Is Used

dbt owns **all** warehouse transformations after Bronze:

- Staging / cleansing
- Standardization
- Multi-timeframe aggregations
- Technical indicators, features, signals
- Tests on model contracts

Python extraction code never computes analytical indicators.

---

# Warehouse Relationships

Unlike OLTP systems, the warehouse uses minimal relational constraints.

- Primary keys identify entities (e.g. `(symbol, open_time)` for klines)
- Physical FKs where operational value is clear (e.g. `pipeline_run_id` → `pipeline_runs`)
- Most analytical joins are logical (exchange + symbol + open_time)

ADR: [../adr/adr_005_physical_foreign_keys.md](../adr/adr_005_physical_foreign_keys.md).

---

# Current Status

**Implemented**

- PostgreSQL 16 warehouse
- Schemas `bronze`, `silver`, `gold`
- Full Bronze DDL + loading
- dbt staging + Silver + Gold models
- Incremental MERGE strategies on analytical models

**Pending (downstream products)**

- BI semantic layers / dashboards
- Trading bot read models beyond SQL
- ML training pipelines
- Additional provider Bronze tables

---

# Future Evolution

The warehouse is designed to support:

- Additional exchanges
- More asset classes
- Richer analytical models
- BI dashboards
- Trading strategies
- Machine Learning pipelines

Those consumers are **not** implemented in the current repository.
