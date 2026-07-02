# Market Data Pipeline – Project Vision and Remaining Roadmap

## Project Vision

The objective of this project is to build a production-oriented ELT pipeline capable of collecting, validating, transforming and serving cryptocurrency market data for two different consumers:

### 1. Business Intelligence

The pipeline should provide clean and structured datasets that allow analysts to explore market behavior through dashboards and reports.

Examples include:

* Market evolution
* Trading volume analysis
* Price trends
* Historical comparisons
* Exchange activity
* Market statistics

The BI layer prioritizes readability, historical completeness and analytical flexibility.

---

### 2. Algorithmic Trading System

The second consumer is an automated trading bot.

Unlike BI, the trading bot requires low-latency access to prepared market information.

The objective is **not** to calculate indicators on demand every time the bot executes.

Instead, the pipeline should continuously prepare and persist market information so the trading bot only needs to query already-computed datasets.

This architecture reduces computation during trading and allows strategies to execute quickly.

The bot should eventually consume:

* Multi-timeframe candles
* Technical indicators
* Trading signals
* Feature datasets
* Strategy-specific analytical tables

The pipeline therefore acts as a market data platform rather than only a data warehouse.

---

# Current Architecture

The project currently implements the following layers.

## Bronze Layer

Implemented.

Responsibilities:

* Extract raw Binance REST API data.
* Validate extracted records.
* Store provider-specific raw datasets.
* Preserve complete historical information.
* Audit every pipeline execution.

Current datasets:

* Current Price
* 24-hour Ticker
* Latest 1-minute Candles

Supporting components:

* Binance Client
* Binance Extractor
* Data Quality
* Bronze Loader
* Pipeline Monitor
* Bronze Pipeline

---

## Silver Layer

Implemented.

Responsibilities:

* Normalize Bronze datasets.
* Create provider-independent models.
* Standardize naming conventions.
* Persist canonical market datasets.
* Build reusable analytical datasets.

Current models:

Staging Views

* stg_binance_price
* stg_binance_ticker_24h
* stg_binance_klines

Incremental Models

* market_snapshot
* market_candles

Current canonical timeframe:

* 1 minute

Silver currently represents the clean operational layer from which downstream models will be generated.

---

# Remaining Silver Development

Although the Silver layer is functional, several important capabilities remain.

## Multi-Timeframe Aggregations

The canonical 1-minute candles should become the source for larger timeframes.

Rather than recalculating candles every time they are requested, the pipeline should continuously build aggregated candles.

Initially supported timeframes:

* 5 minutes
* 15 minutes
* 1 hour
* 4 hours
* 1 day

Each timeframe should become its own incremental dbt model.

Examples:

* market_candles_5m
* market_candles_15m
* market_candles_1h
* market_candles_4h
* market_candles_1d

Each model should correctly aggregate:

* Open
* High
* Low
* Close
* Volume
* Quote Volume
* Number of Trades
* Buy Volumes

These datasets will become the primary source for Gold.

---

## Incremental Aggregations

Aggregated candles should not be rebuilt from the entire historical dataset.

dbt incremental models should process only newly available 1-minute candles.

The aggregation strategy should be efficient enough to support continuous pipeline execution.

---

# Gold Layer

Gold represents the intelligence layer of the platform.

Unlike Silver, Gold should not focus on normalization.

Gold should prepare datasets specifically optimized for downstream consumers.

The primary consumer is the trading bot.

---

## Technical Indicators

Indicators should be calculated separately for every supported timeframe.

Examples include:

* RSI
* EMA
* SMA
* MACD
* ATR
* Bollinger Bands
* VWAP
* ADX

Each indicator should be stored rather than calculated on demand.

---

## Trading Features

Gold should also generate reusable features.

Examples:

* Trend direction
* Momentum
* Volatility
* Volume anomalies
* Support and resistance approximations
* Moving average relationships
* Distance from previous highs/lows

These features should simplify strategy development.

---

## Trading Signals

Gold may also expose reusable signal datasets.

Examples:

* Moving Average Crossovers
* RSI Overbought / Oversold
* MACD Crossovers
* Breakout Signals
* Trend Confirmation
* Volatility Alerts

Signals should remain generic and strategy-independent whenever possible.

---

## Feature Tables

The project should also prepare feature datasets that can later be consumed by:

* Machine Learning models
* Backtesting systems
* Reinforcement Learning experiments
* Statistical analysis

---

# Bootstrap Pipeline

The current Bronze pipeline performs incremental ingestion.

A separate Bootstrap pipeline should also be implemented.

Responsibilities:

* Load complete historical datasets.
* Configure historical depth.
* Bootstrap newly configured symbols.
* Resume interrupted historical loads.
* Prepare the warehouse before incremental execution begins.

Bootstrap should remain independent from the incremental pipeline.

---

# Airflow Orchestration

Once all individual components are complete, Apache Airflow should orchestrate the entire platform.

The final DAG should coordinate multiple independent tasks.

Example workflow:

Start

↓

Bronze Pipeline

↓

dbt Staging

↓

Silver Models

↓

Aggregations

↓

Gold Models

↓

Quality Validation

↓

Completion

Future DAGs may also include:

* Bootstrap DAG
* Incremental DAG
* Daily Maintenance DAG
* Data Quality DAG
* Monitoring DAG

---

# Testing

Testing should evolve beyond the current integration script.

Future testing should include:

Unit Tests

* Extractor
* Loader
* Data Quality
* Monitoring

Integration Tests

* Bronze Pipeline
* Bronze → Silver
* Silver → Gold
* End-to-End Pipeline

Data Tests

dbt tests should validate:

* Unique keys
* Null constraints
* Accepted values
* Referential consistency
* Source freshness

---

# Monitoring

The pipeline should expose operational metrics.

Examples:

* Pipeline duration
* Rows processed
* Failed executions
* Data freshness
* Validation failures
* Aggregation performance

Monitoring information may later be integrated with Airflow.

---

# Documentation

Documentation should continue evolving together with the implementation.

Remaining documentation includes:

* Aggregation Architecture
* Gold Layer
* Airflow Architecture
* Bootstrap Process
* Trading Data Flow
* dbt Lineage
* End-to-End Pipeline Architecture

---

# Final Architecture

The completed platform should resemble the following flow.

Binance REST API

↓

Bronze Pipeline

↓

Bronze Layer

↓

Silver Staging

↓

Silver Canonical Models

↓

Silver Multi-Timeframe Aggregations

↓

Gold Technical Indicators

↓

Gold Trading Features

↓

Gold Trading Signals

↓

Business Intelligence
&
Algorithmic Trading Bot

The final result should be a production-oriented market data platform demonstrating modern Data Engineering practices, scalable ELT architecture, dbt transformations, orchestration with Airflow and reusable analytical datasets for both Business Intelligence and automated trading systems.
