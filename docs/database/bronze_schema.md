# Bronze Layer Physical Schema

## Purpose

The Bronze layer is the entry point of the Data Warehouse.

Its responsibility is to persist raw market data exactly as it is received from external providers while applying only the minimum structural transformations required by the relational model.

The Bronze layer never performs business calculations or analytical transformations.

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
├── binance_klines
├── binance_current_price
└── binance_ticker_24h
```

---

# pipeline_runs

## Purpose

Stores metadata for every pipeline execution.

It allows tracing:

- execution time
- pipeline status
- execution duration
- possible failures

Every Bronze record references the pipeline execution that inserted it.

---

## Main Fields

| Column | Description |
|---------|-------------|
| id | Pipeline execution identifier |
| pipeline_name | Pipeline name |
| status | SUCCESS / FAILED |
| started_at | Execution start |
| finished_at | Execution end |
| duration_ms | Execution duration |
| error_message | Error description if execution failed |

---

# binance_klines

## Source Endpoint

```
GET /api/v3/klines
```

---

## Purpose

Stores candlestick (OHLCV) market data exactly as provided by Binance.

Each row represents one candle for one symbol and one timeframe.

---

## Stored Information

- Symbol
- Open Time
- Open Price
- High Price
- Low Price
- Close Price
- Volume
- Close Time
- Quote Asset Volume
- Number of Trades
- Taker Buy Base Volume
- Taker Buy Quote Volume

---

## Notes

No indicators are calculated in Bronze.

Candles remain exactly as received from Binance.

---

# binance_current_price

## Source Endpoint

```
GET /api/v3/ticker/price
```

---

## Purpose

Stores the latest observed market price for each configured symbol.

This endpoint provides a lightweight snapshot of the current market.

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

Stores rolling 24-hour market statistics.

These values are provided directly by Binance and are not calculated locally.

---

## Stored Information

Examples include:

- Price Change
- Price Change %
- High
- Low
- Volume
- Quote Volume
- Number of Trades
- Bid Price
- Ask Price

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
Bronze Loader
        │
        ▼
Bronze Tables
```

---

# Naming Convention

The Bronze layer uses:

- snake_case
- NUMERIC for decimal values
- TIMESTAMP WITH TIME ZONE for timestamps
- Provider-specific table names

Examples:

```
bronze.binance_klines

bronze.binance_current_price

bronze.binance_ticker_24h
```

---

# Relationships

The Bronze layer keeps relationships to a minimum.

Each data table references the corresponding pipeline execution through `pipeline_run_id`.

No business relationships exist between market tables.

---

# Current Status

Implemented:

- Physical schema
- Table definitions
- PostgreSQL initialization script

Pending:

- Bronze Loader
- Data ingestion
- Incremental loading