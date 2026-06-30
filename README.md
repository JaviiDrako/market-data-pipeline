# Market Data Pipeline

A production-oriented ELT pipeline for collecting, processing and serving cryptocurrency market data using a modern data engineering stack.

The project follows a **Medallion Architecture** (Bronze, Silver and Gold) and is designed to support both Business Intelligence dashboards and algorithmic trading systems through clean, scalable and maintainable data pipelines.

---

# Objectives

This project aims to:

- Collect market data from cryptocurrency exchanges.
- Store raw market data inside a PostgreSQL Data Warehouse.
- Transform raw data into analytics-ready datasets using dbt.
- Serve clean data to BI dashboards.
- Provide high-quality market data for automated trading strategies.
- Follow production-oriented software engineering and data engineering practices.

---

# Current Features

Currently implemented:

- Docker-based local development environment.
- PostgreSQL Data Warehouse.
- Medallion Architecture.
- Bronze schema physical design.
- Configuration-driven symbol management.
- Binance REST API integration.
- Binance market data extraction.
- Bronze loading pipeline.
- Pipeline execution monitoring.
- Multi-provider ready architecture.
- Data quality validation layer.

Planned:

- Airflow DAG orchestration.
- Data Quality layer.
- Silver transformations with dbt.
- Gold analytical models.
- Technical indicators.
- BI Dashboard.
- Trading Bot.

---

# Architecture

The project currently implements the Bronze ingestion pipeline.

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
                Pipeline Monitor
                       │
                       ▼
                Bronze Loader
                       │
                       ▼
                 Bronze Layer
                       │
                      dbt
                       │
                       ▼
                  Silver Layer
                       │
                      dbt
                       │
                       ▼
               Gold Layer
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
Business Intelligence   Trading Bot
```

---

# Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3 |
| Database | PostgreSQL 16 |
| Orchestration | Apache Airflow |
| Transformations | dbt |
| Containers | Docker & Docker Compose |
| Source Control | Git & GitHub |

---

# Project Structure

```
market-data-pipeline/

├── airflow/
├── dbt/
├── docker/
├── docs/
├── src/
│   ├── clients/
│   ├── common/
│   ├── config/
│   ├── extraction/
│   ├── loading/
│   ├── monitoring/
│   └── quality/
└── tests/
```

Project documentation is located under the `docs/` directory.

---

# Current Status

| Component | Status |
|-----------|--------|
| Infrastructure | ✅ |
| PostgreSQL Warehouse | ✅ |
| Bronze Physical Schema | ✅ |
| Binance Client | ✅ |
| Binance Extraction | ✅ |
| Bronze Loader | ✅ |
| Pipeline Monitor | ✅ |
| Data Quality | ✅ |
| Airflow DAGs | ⏳ |
| dbt Models | ⏳ |
| Silver Layer | ⏳ |
| Gold Layer | ⏳ |
| Dashboard | ⏳ |
| Trading Bot | ⏳ |

---

# Getting Started

Clone the repository.

```bash
git clone <repository-url>
```

Copy the environment variables.

```bash
cp docker/.env.example docker/.env
```

Start the services.

```bash
docker compose up
```

---

# Documentation

Additional documentation is available inside the `docs/` directory.

It includes:

- Architecture
- Database
- ADRs
- Diagrams

---

# License

This project is intended for educational purposes and portfolio development.