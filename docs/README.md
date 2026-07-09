# Documentation

This directory contains the technical documentation for the Market Data Pipeline project.

The documentation evolves together with the implementation and records the architecture, database design and engineering decisions taken during development.

---

# Structure

```
docs/

├── adr/
├── architecture/
├── database/
└── diagrams/
```

---

# Contents

## ADR

Architecture Decision Records describing the main architectural decisions adopted during the project.

---

## Architecture

General documentation about the project architecture, Medallion Architecture and orchestration design.

Includes `bootstrap_pipeline.md` for the historical kline Bootstrap Pipeline.

---

## Database

Physical database documentation for every layer of the Data Warehouse.

Currently documented:

- Bronze Layer

Future documentation:

- Silver Layer
- Gold Layer

---

## Diagrams

Architecture and workflow diagrams illustrating the data pipeline.

---

Documentation should always be updated together with the implementation to keep both synchronized.