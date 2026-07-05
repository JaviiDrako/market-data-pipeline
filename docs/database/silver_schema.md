# Silver Layer Physical Schema

## Purpose

The Silver layer transforms raw Bronze data into standardized, analytics-ready datasets.

Unlike the Bronze layer, Silver applies structural transformations, normalization, and data integration while preserving the original business meaning of the data.

The objective is to provide a clean and consistent representation of market information that can be reused by downstream analytical models, aggregations, and Gold layer indicators.

---

# Design Principles

The Silver layer follows these principles:

- Standardized schema
- Provider-independent models
- Incremental processing
- Historical preservation
- Analytics-ready structure
- High query performance

---

# Materialization Strategy

The Silver layer uses different dbt materializations depending on the purpose of each model.

## Staging

Materialization:

```
view
```

Purpose:

- Normalize Bronze tables
- Standardize naming conventions
- Add provider-independent fields
- Expose a clean interface for downstream models

No data is physically duplicated.

---

## Core Silver Models

Materialization:

```
incremental
```

Purpose:

- Persist transformed data
- Process only newly ingested records
- Avoid rebuilding the complete dataset on every execution

Incremental models significantly reduce execution time and resource consumption as the dataset grows.

---

# Current Models

```
silver/

├── stg_binance_price (View)
├── stg_binance_ticker_24h (View)
├── stg_binance_klines (View)
├── market_snapshot (Incremental Table)
└── market_candles (Incremental Table)
```

---

# Staging Models

## stg_binance_price

### Source

```
bronze.binance_price
```

### Purpose

Standardizes the current market price dataset and introduces provider-independent fields.

### Main Transformations

- Adds exchange identifier
- Preserves ingestion timestamp
- Uses standardized naming conventions

---

## stg_binance_ticker_24h

### Source

```
bronze.binance_ticker_24h
```

### Purpose

Standardizes Binance rolling 24-hour market statistics.

### Main Transformations

- Adds exchange identifier
- Preserves all market statistics
- Uses standardized column names

---

## stg_binance_klines

### Source

```
bronze.binance_klines
```

### Purpose

Standardizes candlestick market data.

### Main Transformations

- Adds exchange identifier
- Standardizes field names
- Preserves OHLCV values without modification

---

# market_candles

## Purpose

Stores standardized market candles independently of the original provider.

This model becomes the canonical candle dataset used by downstream aggregations and Gold layer indicator calculations.

---

## Stored Information

- Exchange
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
- Taker Buy Volumes

---

# Multi-Timeframe Aggregations

## Purpose

The multi-timeframe aggregation models build higher timeframe candles from the canonical 1-minute `market_candles`.

Aggregations are performed continuously and incrementally so that consumers (especially the algorithmic trading bot) can query pre-computed candles without on-the-fly calculation.

## Supported Timeframes

- 5 minutes (`market_candles_5m`)
- 15 minutes (`market_candles_15m`)
- 30 minutes (`market_candles_30m`)
- 1 hour (`market_candles_1h`)
- 1 day (`market_candles_1d`)

## Design Principles

- Time alignment to natural boundaries (e.g. 00:00, 00:05 for 5m).
- Only complete windows are materialized (no partial candles).
- Aggregation rules follow standard OHLCV conventions:
  - Open = first open of the window
  - High = max high
  - Low = min low
  - Close = last close
  - Volumes = sum
- Uses dbt incremental + MERGE strategy.
- Small reprocessing window in incremental logic to handle late-arriving or corrected 1m data.
- Lightweight candle attributes (body, wicks, range, direction, typical price, ohlc average) are added for reusability.

## Macros

Reusable logic is centralized:

- `aggregate_candles` macro: handles time bucketing and OHLCV aggregation.
- `candle_attributes` macro: computes objective candle properties.

## Incremental Behavior

- Source data is filtered with a lookback window (3–30 days depending on timeframe).
- Completeness is enforced by counting source 1m candles per bucket.
- If a bucket does not have the exact expected number of 1m candles, it is skipped until the data is complete.

## Usage

These models are the primary source for Gold layer indicators and features.

---

## Materialization

```
incremental
```

---

## Incremental Strategy

The model inserts only candles whose open time is greater than the latest processed candle.

This avoids rebuilding the entire table during every execution.

---

# market_snapshot

## Purpose

Stores standardized market snapshots representing the latest market state observed during each pipeline execution.

Each snapshot combines the current market price with Binance 24-hour statistics.

---

## Stored Information

- Exchange
- Symbol
- Current Price
- 24-hour statistics
- Snapshot Time

---

## Materialization

```
incremental
```

---

## Incremental Strategy

Only snapshots newer than the latest stored snapshot are inserted.

---

# Data Flow

```
Bronze Tables
        │
        ▼
Staging Views
        │
        ▼
Incremental Silver Models
        │
        ▼
Aggregations
        │
        ▼
Gold Layer
```

---

# Incremental Processing

Each pipeline execution follows the workflow below:

```
Bronze Pipeline
        │
        ▼
New Bronze Records
        │
        ▼
dbt run
        │
        ▼
Only New Silver Records
```

This approach minimizes execution time while preserving the complete historical dataset.

---

# Current Status

Implemented

- dbt Project
- PostgreSQL Profile
- Source Definitions
- Staging Views
- Incremental Silver Models
- Integration Test
- Schema Generation Macro

Pending

- Multi-timeframe Aggregations
- Gold Layer
- Technical Indicators
- Airflow Orchestration