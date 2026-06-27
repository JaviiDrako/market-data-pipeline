# ADR-001: Adopt Medallion Architecture

## Status

Accepted

---

## Context

The project requires a scalable architecture capable of supporting raw data ingestion, standardized transformations and analytical models while preserving historical information.

Different consumers such as BI dashboards and trading systems require datasets with different levels of processing.

---

## Decision

The project adopts the Medallion Architecture composed of three layers:

- Bronze
- Silver
- Gold

Each layer has a single responsibility and progressively increases data quality and business value.

---

## Consequences

### Positive

- Clear separation of responsibilities.
- Easier maintenance.
- Supports multiple data sources.
- Preserves raw historical data.
- Simplifies debugging and auditing.

### Negative

- Additional storage requirements.
- More transformation stages.
- Slightly increased implementation complexity.