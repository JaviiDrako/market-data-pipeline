# ADR-002: Use PostgreSQL as the Data Warehouse

## Status

Accepted

---

## Context

The project requires a relational database capable of storing historical market data while remaining lightweight enough for local development.

The selected technology should also be widely used in industry and compatible with dbt and Apache Airflow.

---

## Decision

PostgreSQL has been selected as the project's Data Warehouse.

It stores all Medallion layers and acts as the central persistence layer for analytical workloads.

---

## Consequences

### Positive

- Mature and stable database.
- Excellent SQL support.
- Native compatibility with dbt.
- Easy Docker deployment.
- Strong ecosystem.

### Negative

- Less suitable than columnar databases for very large analytical workloads.
- Future scaling may require partitioning or additional optimization.