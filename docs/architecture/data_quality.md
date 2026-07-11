# Data Quality Layer

## Purpose

The Data Quality layer validates extracted market data **before** it is persisted into the Bronze layer.

It ensures that only structurally valid records enter the Data Warehouse.

The component does **not** transform, normalize or enrich data. It only validates consistency and raises on failure.

Implementation: `src/quality/data_quality.py` (`DataQuality` class).

---

# Position in the Pipeline

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
Data Quality          ← fail-fast gate
        │
        ▼
Bronze Loader
        │
        ▼
Bronze Tables
```

Integrated into:

- `BronzePipeline` (price, ticker, latest klines)
- `BootstrapPipeline` (historical kline batches)

---

# Responsibilities

**Does:**

- Structural validation
- Numeric validation
- Timestamp validation
- Basic consistency checks (e.g. high ≥ low)

**Does not:**

- Data cleaning or imputation
- Normalization (Silver)
- Business transformations / indicators (Gold)
- Soft-fail with partial loads for invalid batches

---

# Validation Strategy

Fail-fast:

1. Validation stops on the first invalid record (per validation call).
2. A `DataQualityError` is raised.
3. The pipeline marks the run as failed via `PipelineMonitor` when applicable.
4. No invalid batch is intentionally committed as “good” data.

---

# Current Validations

## Current Price

- Symbol present and non-empty
- Price numeric and greater than zero

## 24-Hour Ticker

- Symbol present
- Prices non-negative; high ≥ low
- Volumes and trade count non-negative
- Open time before close time

## Klines (latest and historical)

- Symbol present
- OHLC prices positive; high ≥ low
- Volumes and number of trades non-negative
- Open time before close time

---

# Error Handling

Validation failures raise `DataQualityError` (see `src/common/exceptions.py`).

The validation layer never mutates invalid records. Corrections belong in upstream extraction fixes or explicit future cleaning stages—not silent coercion here.

---

# Relationship to dbt Tests

| Layer | When | What |
|-------|------|------|
| Python Data Quality | Pre-Bronze insert | Structural sanity of API payloads |
| dbt tests | Post-transform | Model keys, nullability, uniqueness |

They are complementary, not duplicates.

---

# Current Status

**Implemented**

- Current price, 24h ticker and kline validators
- Fail-fast strategy
- Integration with Bronze and Bootstrap pipelines

**Pending (not implemented)**

- Data quality metrics warehouse / dashboards
- Soft-quarantine tables for rejected rows
- Cross-batch anomaly detection (e.g. price spike alerts)
