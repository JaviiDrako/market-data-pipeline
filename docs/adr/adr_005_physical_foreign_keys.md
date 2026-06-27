# ADR-005: Use Physical Foreign Keys for Pipeline Auditing

## Status

Accepted

---

## Context

Every Bronze record should be traceable to the pipeline execution that produced it.

This improves auditability, debugging and operational monitoring.

---

## Decision

Bronze tables will include a physical foreign key referencing the `pipeline_runs` table.

Market data tables will not use foreign keys between themselves.

Relationships remain minimal and focused on operational traceability.

---

## Consequences

### Positive

- Complete execution traceability.
- Better operational monitoring.
- Strong referential integrity.
- Easier debugging.

### Negative

- Slightly slower insert operations.
- Tighter coupling between Bronze tables and pipeline metadata.