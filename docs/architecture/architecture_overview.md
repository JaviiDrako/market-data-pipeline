# System Architecture Overview

## Purpose

The Market Data Pipeline is a production-oriented ELT platform designed to ingest, process and serve cryptocurrency market data.

The architecture follows a layered approach where every component has a single responsibility. Raw market data is collected from external providers, stored inside a PostgreSQL Data Warehouse, transformed using dbt and finally consumed by Business Intelligence tools and trading systems.

The project has been designed to support additional market data providers without requiring major architectural changes.

---

# High-Level Architecture

```
                    External Market Data Providers
                               │
             ┌─────────────────┴─────────────────┐
             │                                   │
         Binance API                      Future Providers
                                              (Yahoo, etc.)
             │
             ▼
      Market Data Client
             │
             ▼
     Market Data Extractor
             │
             ▼
        Bronze Loader
             │
             ▼
     PostgreSQL Warehouse
             │
     ┌───────┴────────┐
     ▼                ▼
 Bronze            Airflow Metadata
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
     │
 ┌───┴───────────────┐
 ▼                   ▼
BI Dashboards    Trading Bot
```

---

# Component Responsibilities

## Market Data Providers

External APIs providing market information.

Current implementation:

- Binance REST API

Future providers may include:

- Yahoo Finance
- Coinbase
- Kraken
- Polygon
- Alpha Vantage

---

## Client Layer

The Client layer is responsible for communicating with external providers.

Responsibilities:

- Build HTTP requests.
- Execute REST API calls.
- Handle network errors.
- Return raw JSON responses.

Clients do not perform transformations or business logic.

---

## Extraction Layer

The Extraction layer converts provider-specific JSON responses into a standardized Python representation.

Responsibilities:

- Read project configuration.
- Iterate configured symbols.
- Request market data.
- Map JSON responses into Python dictionaries.

The extractor is independent of storage.

---

## Loading Layer

The Loader receives extracted data and persists it into the Bronze layer.

Responsibilities:

- Insert records.
- Manage database transactions.
- Register pipeline executions.
- Handle loading failures.

(Currently under development.)

---

## Bronze Layer

Stores immutable raw market data.

Characteristics:

- One table per provider endpoint.
- No business calculations.
- Historical preservation.
- Complete auditability.

---

## Silver Layer

Stores standardized and validated datasets.

Responsibilities:

- Data cleansing.
- Standardized naming.
- Type normalization.
- Cross-provider consistency.

---

## Gold Layer

Contains business-oriented analytical models.

Examples:

- Technical indicators.
- Aggregated OHLC candles.
- Trading signals.
- Dashboard-ready datasets.

---

# Configuration

Project behavior is configuration-driven.

Configuration currently includes:

- Market symbols
- Historical extraction settings
- Provider configuration

The architecture allows adding new providers without modifying the extraction workflow.

---

# Current Implementation Status

Implemented:

- Docker infrastructure
- PostgreSQL warehouse
- Bronze physical schema
- Binance REST client
- Binance extractor

Pending:

- Bronze Loader
- Airflow DAGs
- dbt transformations
- Silver layer
- Gold layer
- BI dashboard
- Trading bot

---

# Design Principles

The project follows the following engineering principles:

- Single Responsibility Principle
- Separation of Concerns
- Configuration over Hardcoding
- Extensibility
- Layered Architecture
- Medallion Architecture