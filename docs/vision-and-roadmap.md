# Market Data Pipeline – Project Vision and Roadmap

## Project Vision

Build a production-oriented ELT platform that collects, validates, transforms and serves cryptocurrency market data for two primary future consumers:

### 1. Business Intelligence (pending)

Clean, historical, analytics-ready datasets for dashboards and reports:

- Market evolution and price trends
- Volume analysis and exchange activity
- Historical comparisons and market statistics

The BI layer prioritizes readability, historical completeness and analytical flexibility.

### 2. Algorithmic Trading System (pending)

An automated trading bot should **consume pre-computed datasets**, not recalculate indicators on every decision cycle.

The bot should eventually query:

- Multi-timeframe candles (Silver)
- Technical indicators (Gold)
- Trading signals (Gold)
- Feature datasets / feature tables (Gold)

The pipeline therefore acts as a **market data platform**, not only a passive warehouse.

### 3. Machine Learning (pending)

Feature tables (`gold.market_dataset_*`) are designed to support future ML training, backtesting and experimentation. No ML training pipeline is implemented in this repository.

---

# What is implemented today

The platform already covers the full ELT path from Binance API to Gold feature tables, with orchestration and tests.

## Bronze Layer — ✅ Implemented

Responsibilities:

- Extract raw Binance REST data (price, 24h ticker, klines)
- Validate extracted records (Data Quality)
- Persist provider-specific raw tables
- Audit every execution (`pipeline_runs`)
- Control historical bootstrap (`configured_symbols`)

Components:

- `BinanceClient`, `BinanceExtractor`
- `DataQuality`
- `BinanceLoader`
- `PipelineMonitor`
- `BronzePipeline` (incremental)
- `BootstrapPipeline` (historical klines)

## Silver Layer — ✅ Implemented

Responsibilities:

- Normalize Bronze via staging views
- Persist canonical 1-minute candles
- Build multi-timeframe OHLCV aggregations incrementally
- Persist market snapshots

Models:

| Model | Role |
|-------|------|
| `stg_binance_price` | Staging view |
| `stg_binance_ticker_24h` | Staging view |
| `stg_binance_klines` | Staging view |
| `market_candles` | Canonical 1m candles |
| `market_candles_5m` / `_15m` / `_30m` / `_1h` / `_1d` | Aggregated timeframes |
| `market_snapshot` | Price + 24h stats snapshot |

## Gold Layer — ✅ Implemented

Intelligence layer optimized for consumption (not normalization).

```
market_candles_*
      → market_indicators_*
      → market_features_*
      → market_signals_*
      → market_dataset_*     ← primary consumable tables
```

Includes:

- Technical indicators (EMA, SMA, RSI, MACD, ATR, Bollinger, …)
- Trading features (trend, momentum, volatility, price action)
- Generic signals (alignment, RSI zones, MACD crosses, breakouts, …)
- Feature tables (keys + features + signals only)

## Bootstrap Pipeline — ✅ Implemented

- Historical klines only (blocks of 1000 — Binance API limit)
- Config-driven symbols and depth (`Settings` / `config.yaml`)
- Resume via `last_bootstrap_open_time`
- Status machine on `configured_symbols`
- Independent of the incremental Bronze path

## Airflow Orchestration — ✅ Implemented (two DAGs)

| DAG | Schedule | Flow |
|-----|----------|------|
| `incremental_market_data` | From `config.yaml` interval → cron | `BronzePipeline` → `dbt build` |
| `bootstrap_market_data` | Manual | `BootstrapPipeline` → `dbt build` |

## Testing — ✅ Implemented

| Type | Location | Examples |
|------|----------|----------|
| Unit | `tests/unit/` | Extractor, bootstrap helpers, interval→cron |
| Integration | `tests/integration/` | E2E pipeline, bootstrap, 1m→5m aggregation |
| dbt tests | `dbt/models/**/*.yml` | not_null / uniqueness on keys where defined |

## Monitoring — ✅ Implemented (pipeline-level)

- `bronze.pipeline_runs` records start/finish, status, row counts, errors
- Used by both incremental and bootstrap pipelines

## Data Quality — ✅ Implemented (pre-Bronze)

- Fail-fast structural validation before load
- Integrated into `BronzePipeline` and bootstrap kline path

## Documentation — ✅ This sprint

- Root README suitable for clone-and-run onboarding
- Architecture, database and ADR index aligned with implementation

---

# What is NOT implemented (pending)

Do **not** document or demo these as if they were live.

| Area | Status | Notes |
|------|--------|-------|
| **BI / Dashboards** | ⏳ Pending | No dashboard project, no BI tool integration |
| **Trading Bot** | ⏳ Pending | No execution engine, no order management |
| **Machine Learning** | ⏳ Pending | Feature tables exist; no training/serving pipeline |
| Additional exchanges | ⏳ Pending | Architecture is multi-provider ready; only Binance is live |
| Maintenance / ops DAG on mainline | ⏳ Pending | May exist on a feature branch; not part of current develop baseline |
| Advanced DQ metrics dashboards | ⏳ Pending | Structural validation exists; no metrics warehouse/UI |
| Real-time / WebSocket streaming | ⏳ Pending | REST polling only |

---

# Target end-state architecture

```
Binance REST API (and future providers)
        ↓
Bronze Pipeline / Bootstrap Pipeline
        ↓
Bronze Layer
        ↓
Silver Staging + Canonical Candles
        ↓
Silver Multi-Timeframe Aggregations
        ↓
Gold Technical Indicators
        ↓
Gold Trading Features
        ↓
Gold Trading Signals
        ↓
Gold Feature Tables
        ↓
┌───────────────┬──────────────────┬────────────────────┐
│ BI Dashboards │  Trading Bot     │  ML / Backtesting  │
│   (pending)   │   (pending)      │     (pending)      │
└───────────────┴──────────────────┴────────────────────┘
```

The data platform path through **Gold Feature Tables** is implemented. Downstream product layers remain future work.

---

# Recommended next development themes

1. **BI layer** — connect a BI tool (e.g. Metabase, Superset) to `silver` / `gold` read models.
2. **Trading bot prototype** — read-only consumer of `market_dataset_*` + risk rules (out of scope for pure DE until defined).
3. **ML experiments** — export feature tables; train offline models without coupling to Airflow at first.
4. **Ops hardening** — maintenance DAG, freshness alerts, richer DQ metrics.
5. **Second provider** — prove multi-provider Silver normalization.

---

# Final note

This repository demonstrates modern Data Engineering practices: Medallion Architecture, configuration-driven ingestion, resumable historical loads, dbt incremental models, Airflow orchestration, and automated tests.

It is **ready to present as a Data Engineering portfolio project**. BI, trading and ML products are intentional next steps—not missing half-finished claims inside the current codebase.
