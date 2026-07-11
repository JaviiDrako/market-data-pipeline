# Architecture Decision Records (ADR)

This directory records significant architectural decisions for the Market Data Pipeline.

Each ADR captures **context**, **decision**, and **consequences**. ADRs are not rewritten when implementation details evolve unless the **decision itself** changes.

---

## Index

| ID | Title | Status |
|----|-------|--------|
| [ADR-001](adr_001_medallion_architecture.md) | Adopt Medallion Architecture | Accepted |
| [ADR-002](adr_002_postgresql_as_data_warehouse.md) | PostgreSQL as Data Warehouse | Accepted |
| [ADR-003](adr_003_provider-specific_bronze_tables.md) | Provider-specific Bronze tables | Accepted |
| [ADR-004](adr_004_persist_gold_models.md) | Persist Gold analytical models | Accepted |
| [ADR-005](adr_005_physical_foreign_keys.md) | Selective physical foreign keys | Accepted |

---

## When to add an ADR

Add a new ADR when you:

- Choose a durable technology or pattern (e.g. warehouse engine, orchestration style)
- Change a layering or persistence strategy
- Accept a non-obvious trade-off that future contributors must understand

Do **not** create ADRs for routine feature work or documentation-only sprints.

---

## Review note (Sprint 7)

All five ADRs still match the implemented architecture:

- Medallion Bronze → Silver → Gold is the active layout
- PostgreSQL remains the warehouse
- Bronze stays provider-specific
- Gold models are physically persisted (incremental MERGE tables)
- Physical FKs remain selective (e.g. `pipeline_run_id`)

No ADR was superseded during the documentation review.
