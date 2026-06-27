# Data Warehouse Architecture

## Purpose

The project uses a PostgreSQL Data Warehouse to centralize market data collected from cryptocurrency exchanges.

Instead of querying external APIs directly from analytical applications, all market information is first stored inside the warehouse.

This approach provides:

- Historical persistence
- Better query performance
- Data consistency
- Reproducible analytics
- Support for multiple consumers

---

# Why a Data Warehouse?

A Data Warehouse separates operational data collection from analytical consumption.

Instead of repeatedly querying external APIs, data is collected once and reused by:

- BI dashboards
- Trading algorithms
- Machine learning models
- Future analytical services

---

# Medallion Architecture

The warehouse follows the Medallion Architecture.

```
Bronze
   │
   ▼
Silver
   │
   ▼
Gold
```

Each layer progressively increases data quality and business value.

---

# Bronze Layer

Purpose:

Store raw provider data with minimal transformation.

Characteristics:

- Immutable
- Auditable
- Provider-specific
- Historical

Examples:

- binance_klines
- binance_current_price
- binance_ticker_24h

Only structural mapping is performed.

No business calculations are allowed.

---

# Silver Layer

Purpose:

Standardize data coming from different providers.

Responsibilities:

- Standardized column names
- Type normalization
- Data validation
- Provider abstraction

The Silver layer removes provider-specific differences while preserving information.

---

# Gold Layer

Purpose:

Provide analytical datasets ready for consumption.

Examples:

- Technical indicators
- Aggregated candles
- Dashboard models
- Trading datasets

Gold prioritizes query performance over normalization.

---

# Why Bronze Tables Are Provider-Specific

The Bronze layer stores provider responses as close as possible to the original API.

For example:

```
bronze.binance_klines

bronze.yahoo_ohlc
```

Different providers may expose different fields.

Instead of forcing an artificial standardization during ingestion, normalization occurs later in the Silver layer.

This design minimizes data loss and simplifies future integrations.

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
Bronze Loader
      │
      ▼
Bronze Tables
      │
      ▼
dbt
      │
      ▼
Silver
      │
      ▼
dbt
      │
      ▼
Gold
```

---

# Why dbt Is Used

dbt is responsible for all warehouse transformations.

Responsibilities include:

- Data cleaning
- Standardization
- Business transformations
- Technical indicators
- Aggregations

Extraction code never performs analytical transformations.

---

# Warehouse Relationships

Unlike transactional databases, the warehouse minimizes relational constraints.

Primary keys are used for entity identification.

Physical foreign keys are only applied where they provide operational value.

Relationships are primarily logical and maintained through consistent identifiers.

---

# Current Status

Implemented:

- PostgreSQL warehouse
- Bronze schema
- Bronze table design

Pending:

- Bronze loading
- Silver models
- Gold models
- dbt transformations
- Analytical indicators

---

# Future Evolution

The warehouse has been designed to support:

- Additional exchanges
- Multiple asset classes
- Additional analytical models
- Trading strategies
- Business Intelligence dashboards
- Machine Learning pipelines