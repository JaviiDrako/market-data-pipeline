# Airflow Architecture – Market Data DAGs

## Purpose

Apache Airflow orchestrates the market data pipelines.

It does **not** contain business logic. It only schedules (or triggers) and invokes:

| Component | Role |
|-----------|------|
| `BronzePipeline` | Incremental extract → validate → load into Bronze |
| `BootstrapPipeline` | Historical kline load into Bronze |
| `dbt build` | Staging → Silver → Gold transformations |

All business logic remains in `src/pipelines/` and `dbt/`.

---

## Two DAGs (current mainline)

| | Incremental | Bootstrap |
|--|-------------|-----------|
| **DAG id** | `incremental_market_data` | `bootstrap_market_data` |
| **File** | `airflow/dags/incremental_market_data_dag.py` | `airflow/dags/bootstrap_market_data_dag.py` |
| **Schedule** | From `config.yaml` interval → cron | **None** (manual only) |
| **When to use** | Continuous production loads | Initial / resume historical load |
| **Pipeline** | `BronzePipeline` | `BootstrapPipeline` |
| **Then** | `dbt build` | `dbt build` |
| **catchup** | `False` | `False` |
| **max_active_runs** | `1` | `1` |
| **owner** | `market-data` | `market-data` |
| **retries** | `1` (delay 2 min) | `1` (delay 2 min) |

Both DAGs are independent. Running one does not replace the other.

> A daily **maintenance** DAG is **not** part of the current `develop` baseline. Do not assume it exists unless merged from a feature branch.

---

## When to use each DAG

### Incremental (`incremental_market_data`)

- Scheduled automatically (e.g. every minute if `interval: 1m`).
- Loads the **latest** price, 24h ticker, and klines.
- Run continuously in production after bootstrap has completed.

### Bootstrap (`bootstrap_market_data`)

- **No schedule** — trigger only from the UI or CLI.
- Loads **historical** klines for symbols in `config.yaml` / `configured_symbols`.
- Uses `history_days` from Settings (`sources.binance.historical.days`).
- Supports resume via `last_bootstrap_open_time`.
- Use once per environment (or after adding symbols / failed history).

Typical order for a new environment:

1. Trigger **Bootstrap** (manual) → historical Bronze + dbt.  
2. Enable **Incremental** schedule → ongoing updates.

---

## Flows

### Incremental

```
start
  ↓
run_bronze_pipeline   →  BronzePipeline.run(dag_run_id)
  ↓
run_dbt_build         →  dbt build (full project graph)
  ↓
finish
```

### Bootstrap

```
start
  ↓
run_bootstrap_pipeline   →  BootstrapPipeline.run(dag_run_id)
  ↓
run_dbt_build            →  dbt build (full project graph)
  ↓
finish
```

In both cases:

- `dbt build` runs only if the previous pipeline task succeeds.
- dbt resolves model dependencies; the DAGs do not select individual models.

---

## Incremental schedule frequency

The incremental schedule is **not** hard-coded in the DAG.

### Source of truth

```yaml
# src/config/config.yaml
sources:
  binance:
    historical:
      interval: 1m    # ← controls incremental Airflow schedule
      days: 100       # ← controls bootstrap history depth
```

### Resolution path (incremental only)

```
config.yaml
    ↓
Settings.get_history_interval("binance")
    ↓
interval_to_cron(interval)   # src/common/interval_cron.py
    ↓
Airflow schedule (cron)
```

Also available as:

```python
Settings().get_pipeline_schedule("binance")
```

### Interval → cron mapping

| Interval | Cron | Meaning |
|----------|------|---------|
| `1m` | `* * * * *` | Every minute |
| `5m` | `*/5 * * * *` | Every 5 minutes |
| `15m` | `*/15 * * * *` | Every 15 minutes |
| `30m` | `*/30 * * * *` | Every 30 minutes |
| `1h` | `0 * * * *` | Every hour |
| `1d` | `0 0 * * *` | Daily at 00:00 UTC |

### How to change the incremental frequency

1. Edit `src/config/config.yaml` → `sources.binance.historical.interval`.
2. Wait for the Airflow scheduler to re-parse DAGs (or restart).
3. No DAG code changes are required.

Bootstrap remains manual regardless of `interval`.

---

## Runtime environment (Docker)

Airflow services mount the repository at `/opt/airflow/project` and set:

| Variable | Purpose |
|----------|---------|
| `PROJECT_ROOT` | Path to the repo inside the container |
| `PYTHONPATH` | Import `src.*` from DAGs |
| `WAREHOUSE_HOST` / `WAREHOUSE_PORT` | Postgres on Docker network (`postgres:5432`) |
| `DBT_*` | dbt connection for `dbt/profiles.yml` |

Dependencies (`dbt-postgres`, `psycopg`, etc.) are installed via Airflow’s `_PIP_ADDITIONAL_REQUIREMENTS`.

dbt uses writable paths under `/tmp` for logs and target inside the container.

---

## Manual triggers

### Incremental

```bash
docker exec market_data_airflow_scheduler \
  airflow dags unpause incremental_market_data

docker exec market_data_airflow_scheduler \
  airflow dags trigger incremental_market_data
```

### Bootstrap

```bash
docker exec market_data_airflow_scheduler \
  airflow dags unpause bootstrap_market_data

docker exec market_data_airflow_scheduler \
  airflow dags trigger bootstrap_market_data
```

UI: `http://localhost:8080` → select DAG → Trigger.

Confirm tasks end in **success** for both DAGs.

---

## Design decisions

| Decision | Rationale |
|----------|-----------|
| Two separate DAGs | Different cadence (scheduled vs manual) and different pipelines |
| TaskFlow + EmptyOperator | Clear task names; same style across DAGs |
| Bootstrap `schedule=None` | Historical load is intentional, not periodic |
| `retries=1`, `retry_delay=2m` | Tolerate transient Binance/DB blips |
| `max_active_runs=1` | Avoid concurrent heavy loads / merges |
| Logging (not print) | Airflow task logs only |
| No SQL / no business logic in DAGs | All logic in `src/pipelines` and dbt |
| Shared `AIRFLOW__WEBSERVER__SECRET_KEY` + `airflow_logs` volume | Webserver can serve scheduler task logs without 403s |

---

## Out of scope / pending orchestration

Not implemented on the current mainline:

- Daily maintenance / data-quality ops DAG
- Separate DQ-only or monitoring-only DAGs
- Multi-environment deployment topologies beyond local Docker Compose
