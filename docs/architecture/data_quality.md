# Data Quality Layer

## Purpose

The Data Quality layer validates extracted market data before it is persisted into the Bronze layer.

Its responsibility is to ensure that only structurally valid records are stored inside the Data Warehouse.

The component does not transform, normalize or enrich data.

It only validates consistency.

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
Data Quality
        │
        ▼
Bronze Loader
        │
        ▼
Bronze Tables
```

---

# Responsibilities

The Data Quality layer performs:

- Structural validation
- Numeric validation
- Timestamp validation
- Basic consistency validation

It does not perform:

- Data cleaning
- Data normalization
- Business transformations
- Technical indicator calculations

Those responsibilities belong to later pipeline stages.

---

# Validation Strategy

The project follows a fail-fast validation strategy.

If any record is invalid:

1. Validation stops immediately.
2. A `DataQualityError` is raised.
3. The pipeline execution is marked as failed.
4. No invalid data is inserted into Bronze.

---

# Current Validations

## Current Price

- Symbol exists
- Symbol is not empty
- Price is numeric
- Price is greater than zero

---

## 24-Hour Ticker

- Symbol exists
- Prices are non-negative
- High price is greater than or equal to low price
- Volumes are non-negative
- Trade count is non-negative
- Open time is before close time

---

## Latest Klines

- Symbol exists
- OHLC prices are positive
- High price is greater than or equal to low price
- Volumes are non-negative
- Number of trades is non-negative
- Open time is before close time

---

# Error Handling

Validation failures raise a `DataQualityError`.

The validation layer never attempts to modify invalid records.

All corrections, if required in the future, must be implemented outside this component.

---

# Current Status

Implemented:

- Current price validation
- 24-hour ticker validation
- Latest kline validation
- Fail-fast validation strategy

Pending:

- Integration with the Bronze Pipeline
- Data quality metrics
- Validation reports