# Documentation

Technical documentation for the **Market Data Pipeline**.

Documentation evolves with the implementation and records architecture, database design, and engineering decisions. It must stay synchronized with the code on `develop`.

---

## How to navigate

| If you want… | Start here |
|--------------|------------|
| Clone and run the project | Root [`README.md`](../README.md) |
| Understand the full platform vision | [`vision-and-roadmap.md`](vision-and-roadmap.md) |
| Understand system components | [`architecture/architecture_overview.md`](architecture/architecture_overview.md) |
| Understand warehouse layers | [`architecture/warehouse_architecture.md`](architecture/warehouse_architecture.md) |
| Understand historical bootstrap | [`architecture/bootstrap_pipeline.md`](architecture/bootstrap_pipeline.md) |
| Understand Airflow DAGs | [`architecture/airflow_architecture.md`](architecture/airflow_architecture.md) |
| Understand pre-load validation | [`architecture/data_quality.md`](architecture/data_quality.md) |
| Inspect table/model schemas | [`database/`](database/) |
| Read architectural decisions | [`adr/`](adr/) |

---

## Directory structure

```
docs/
├── README.md                 # This index
├── vision-and-roadmap.md     # Product vision + implemented vs pending
├── adr/                      # Architecture Decision Records
├── architecture/             # System design documents
├── database/                 # Physical / logical layer schemas
└── diagrams/                 # Reserved for additional diagram assets
```

---

## Architecture

| Document | Description | Status |
|----------|-------------|--------|
| [architecture_overview.md](architecture/architecture_overview.md) | High-level components, pipelines, configuration | Current |
| [warehouse_architecture.md](architecture/warehouse_architecture.md) | Medallion warehouse design and data flow | Current |
| [bootstrap_pipeline.md](architecture/bootstrap_pipeline.md) | Historical kline bootstrap, resume, `configured_symbols` | Current |
| [airflow_architecture.md](architecture/airflow_architecture.md) | Incremental + Bootstrap DAGs, schedule mapping | Current |
| [data_quality.md](architecture/data_quality.md) | Pre-Bronze structural validation | Current |

### Topics covered across architecture docs

- Incremental Pipeline (`BronzePipeline` + `dbt build`)
- Bootstrap Pipeline (`BootstrapPipeline` + `dbt build`)
- Airflow DAGs (`incremental_market_data`, `bootstrap_market_data`)
- Bronze / Silver / Gold responsibilities
- Bootstrap configuration via `Settings` / `config.yaml`
- `configured_symbols` control table
- Monitoring (`pipeline_runs` / `PipelineMonitor`)
- Data Quality (`DataQuality`)
- Testing approach (unit + integration; see root README)

---

## Database

| Document | Description | Status |
|----------|-------------|--------|
| [bronze_schema.md](database/bronze_schema.md) | Bronze tables, `pipeline_runs`, `configured_symbols` | Current |
| [silver_schema.md](database/silver_schema.md) | Staging, `market_candles`, multi-TF aggregations, snapshot | Current |
| [gold_schema.md](database/gold_schema.md) | Indicators, features, signals, feature tables | Current |

---

## ADRs

| Document | Decision |
|----------|----------|
| [adr/README.md](adr/README.md) | ADR index |
| [adr_001](adr/adr_001_medallion_architecture.md) | Medallion Architecture |
| [adr_002](adr/adr_002_postgresql_as_data_warehouse.md) | PostgreSQL as Data Warehouse |
| [adr_003](adr/adr_003_provider-specific_bronze_tables.md) | Provider-specific Bronze tables |
| [adr_004](adr/adr_004_persist_gold_models.md) | Persist Gold analytical models |
| [adr_005](adr/adr_005_physical_foreign_keys.md) | Selective physical foreign keys |

---

## Vision and roadmap

| Document | Description |
|----------|-------------|
| [vision-and-roadmap.md](vision-and-roadmap.md) | Project vision, implemented platform, and **explicitly pending** work (BI, Trading Bot, ML, …) |

---

## Conventions

1. Documentation language: **English** (code and docs).
2. Do **not** document unimplemented features as if they were live.
3. Update docs in the same sprint as behavioural changes.
4. Prefer linking to a single source of truth over duplicating long sections.
5. Diagrams use fenced Markdown code blocks (ASCII / text).
