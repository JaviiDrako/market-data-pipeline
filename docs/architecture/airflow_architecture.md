# Airflow Architecture – Market Data DAGs

## Purpose

Apache Airflow orchestrates the market data pipelines **and** daily system health checks.

It does **not** contain business logic for extraction or transformation. Pipelines and dbt own that work. The maintenance DAG only **validates** warehouse state.

| Component | Role |
|-----------|------|
| `BronzePipeline` | Incremental extract → validate → load into Bronze |
| `BootstrapPipeline` | Historical kline load into Bronze |
| `dbt build` | Staging → Silver → Gold transformations |
| `maintenance_checks` | Read-only data quality / freshness checks |

All pipeline logic remains in `src/pipelines/` and `dbt/`.  
Maintenance checks live in `src/quality/maintenance_checks.py`.

---

## Three DAGs

```
┌─────────────────────────┐
│ incremental_market_data │  scheduled (config interval → cron)
│ BronzePipeline → dbt    │
└─────────────────────────┘

┌─────────────────────────┐
│ bootstrap_market_data   │  manual only (schedule=None)
│ BootstrapPipeline → dbt │
└─────────────────────────┘

┌─────────────────────────┐
│ maintenance_pipeline    │  daily (00:00 UTC)
│ health / quality checks │  (no extract, no dbt)
└─────────────────────────┘
```

| | Incremental | Bootstrap | Maintenance |
|--|-------------|-----------|-------------|
| **DAG id** | `incremental_market_data` | `bootstrap_market_data` | `maintenance_pipeline` |
| **File** | `airflow/dags/incremental_market_data_dag.py` | `airflow/dags/bootstrap_market_data_dag.py` | `airflow/dags/maintenance_pipeline_dag.py` |
| **Schedule** | From `config.yaml` interval → cron | **None** (manual) | **Daily** `0 0 * * *` |
| **When to use** | Continuous production loads | Initial / resume historical load | Daily health monitoring |
| **Runs** | `BronzePipeline` + `dbt build` | `BootstrapPipeline` + `dbt build` | Validation checks only |
| **catchup** | `False` | `False` | `False` |
| **max_active_runs** | `1` | `1` | `1` |
| **owner** | `market-data` | `market-data` | `market-data` |
| **retries** | `1` (2 min) | `1` (2 min) | `1` (2 min) |

The three DAGs are independent. None replaces another.

---

## When to use each DAG

### Incremental (`incremental_market_data`)

- Scheduled automatically (e.g. every minute if `interval: 1m`).
- Loads the **latest** price, 24h ticker, and klines.
- Production path after bootstrap has completed.

### Bootstrap (`bootstrap_market_data`)

- **No schedule** — trigger only from the UI or CLI.
- Loads **historical** klines for symbols in `config.yaml` / `configured_symbols`.
- Uses `history_days` from Settings.
- Supports resume via `last_bootstrap_open_time`.

### Maintenance (`maintenance_pipeline`)

- Runs **once per day** (00:00 UTC) or on demand via Trigger.
- **Does not** load data or run dbt.
- Fails loudly if the warehouse looks unhealthy (stale klines, failed bootstrap, empty Gold, etc.).

Typical environment lifecycle:

1. Trigger **Bootstrap** (manual) → historical Bronze + dbt.  
2. Enable **Incremental** schedule → ongoing updates.  
3. Keep **Maintenance** enabled → daily automated checks.

---

## Flows

### Incremental

```
start
  ↓
run_bronze_pipeline   →  BronzePipeline.run(dag_run_id)
  ↓
run_dbt_build         →  dbt build
  ↓
finish
```

### Bootstrap

```
start
  ↓
run_bootstrap_pipeline   →  BootstrapPipeline.run(dag_run_id)
  ↓
run_dbt_build            →  dbt build
  ↓
finish
```

### Maintenance

```
start
  ↓
check_pipeline_runs       →  latest bronze.pipeline_runs status = success
  ↓
check_configured_symbols  →  all enabled; none bootstrap_status=failed
  ↓
check_bronze_freshness    →  MAX(open_time) within threshold
  ↓
check_gold_tables         →  5m indicators/features/signals/dataset non-empty
  ↓
check_gold_consistency    →  equal row counts on 5m Gold layers
  ↓
finish
```

If any check raises, the task fails (and downstream tasks do not run).

---

## Maintenance checks (detail)

Implemented in `src/quality/maintenance_checks.py` (reusable; DAG only calls them).

| Task | Validation |
|------|------------|
| `check_pipeline_runs` | Latest `bronze.pipeline_runs` row has `status='success'` |
| `check_configured_symbols` | All rows `enabled=true`; none `bootstrap_status='failed'` |
| `check_bronze_freshness` | `MAX(open_time)` on `bronze.binance_klines` is not older than **2 hours** (`BRONZE_FRESHNESS_MAX_AGE`) |
| `check_gold_tables` | `gold.market_indicators_5m`, `_features_5m`, `_signals_5m`, `_dataset_5m` each have ≥ 1 row |
| `check_gold_consistency` | Those four 5m tables have **equal** `COUNT(*)` |

### Bronze freshness threshold

Default: **2 hours**.

Rationale: incremental may run every minute; a 2-hour lag tolerates brief outages without false positives, while still detecting a stuck pipeline.

---

## Incremental schedule frequency

Not hard-coded in the DAG.

```yaml
# src/config/config.yaml
sources:
  binance:
    historical:
      interval: 1m    # ← incremental Airflow schedule
      days: 100       # ← bootstrap history depth
```

```
config.yaml → Settings.get_history_interval → interval_to_cron → Airflow schedule
```

| Interval | Cron |
|----------|------|
| `1m` | `* * * * *` |
| `5m` | `*/5 * * * *` |
| `15m` | `*/15 * * * *` |
| `30m` | `*/30 * * * *` |
| `1h` | `0 * * * *` |
| `1d` | `0 0 * * *` |

---

## Runtime environment (Docker)

| Variable | Purpose |
|----------|---------|
| `PROJECT_ROOT` | Repo path in container |
| `PYTHONPATH` | Import `src.*` from DAGs |
| `WAREHOUSE_HOST` / `WAREHOUSE_PORT` | Postgres on Docker network |
| `DBT_*` | dbt profiles for pipeline DAGs |
| `AIRFLOW__WEBSERVER__SECRET_KEY` | Shared across components (UI logs) |

Shared volume `airflow_logs` → `/opt/airflow/logs` for UI task log serving.

---

## Manual triggers

```bash
# Incremental
docker exec market_data_airflow_scheduler airflow dags trigger incremental_market_data

# Bootstrap
docker exec market_data_airflow_scheduler airflow dags trigger bootstrap_market_data

# Maintenance
docker exec market_data_airflow_scheduler airflow dags unpause maintenance_pipeline
docker exec market_data_airflow_scheduler airflow dags trigger maintenance_pipeline
```

UI: `http://localhost:8080` → select DAG → Trigger.

---

## Design decisions

| Decision | Rationale |
|----------|-----------|
| Three separate DAGs | Different cadence and responsibilities (scheduled load, manual history, daily health) |
| TaskFlow + EmptyOperator | Clear task names; same style across all DAGs |
| Bootstrap `schedule=None` | Historical load is intentional, not periodic |
| Maintenance has no extract/dbt | Pure observability / quality gate |
| Checks in `src/quality` | Reusable, unit-testable, DAG stays thin |
| Daily schedule for maintenance | Enough for ops alerts without noise |
| `retries=1`, `retry_delay=2m` | Tolerate transient Binance/DB blips |
| `max_active_runs=1` | Avoid concurrent heavy loads / merges / overlapping checks |
| Logging (not print) | Airflow task logs only |
| No SQL / no business logic in DAGs | Pipeline logic in `src/pipelines` and dbt; checks in `src/quality` |
| Shared `AIRFLOW__WEBSERVER__SECRET_KEY` + `airflow_logs` volume | Webserver can serve scheduler task logs without 403s |

---

## Out of scope / pending orchestration

Not implemented on the current mainline:

- Multi-environment deployment topologies beyond local Docker Compose
- Separate alerting integrations (webhooks / Slack) wired to maintenance failures
- Dataset-aware scheduling between incremental completion and maintenance
