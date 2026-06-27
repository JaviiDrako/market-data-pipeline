# ADR-004: Persist Gold Analytical Models

## Status

Accepted

---

## Context

Technical indicators and aggregated analytical datasets are frequently consumed by BI dashboards and trading systems.

Recomputing them on every query would unnecessarily increase latency and computational cost.

---

## Decision

Gold analytical models will be physically persisted inside the warehouse.

dbt will be responsible for creating and refreshing these datasets.

---

## Consequences

### Positive

- Faster analytical queries.
- Lower computational overhead.
- Better support for automated trading.
- Predictable query performance.

### Negative

- Increased storage usage.
- Requires refresh orchestration.