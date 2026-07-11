# Diagrams

Architecture diagrams for the Market Data Pipeline, authored in **Mermaid**.

They render natively on GitHub, GitLab, and most modern Markdown viewers.

| Diagram | File | Description |
|---------|------|-------------|
| General architecture | [architecture_overview.md](architecture_overview.md) | End-to-end platform components |
| Incremental flow | [incremental_flow.md](incremental_flow.md) | Scheduled Bronze → dbt path |
| Bootstrap flow | [bootstrap_flow.md](bootstrap_flow.md) | Historical kline load + resume |
| Medallion layers | [medallion_architecture.md](medallion_architecture.md) | Bronze / Silver / Gold data products |

Also referenced from:

- Root [`README.md`](../../README.md)
- [`docs/README.md`](../README.md)
- [`docs/architecture/architecture_overview.md`](../architecture/architecture_overview.md)
