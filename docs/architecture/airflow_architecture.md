# Airflow Architecture – Incremental DAG

## Purpose

Apache Airflow orchestrates the **incremental production pipeline**.

It does **not** contain business logic. It only schedules and invokes:

1. `BronzePipeline` (Python) – latest market data into Bronze  
2. `dbt build` – staging → silver → gold transformations  

Bootstrap and maintenance DAGs are out of scope for this document (future sprints).

---

## Incremental DAG

| Field | Value |
|-------|--------|
| **DAG id** | `incremental_market_data` |
| **File** | `airflow/dags/incremental_market_data_dag.py` |
| **Schedule** | Derived from `config.yaml` (not hard-coded in the DAG) |
| **Catchup** | `False` |
| **max_active_runs** | `1` (no overlapping incremental runs) |

### Flow

```
start
  ↓
run_bronze_pipeline   →  BronzePipeline.run(dag_run_id)
  ↓
run_dbt_build         →  dbt build (full project graph)
  ↓
finish
```

`dbt build` runs the entire project; dbt resolves model dependencies. The DAG does not select individual models.

---

## Schedule frequency

The schedule is **not** hard-coded in the DAG.

### Source of truth

```yaml
# src/config/config.yaml
sources:
  binance:
    historical:
      interval: 1m    # ← controls incremental Airflow schedule
      days: 100
```

### Resolution path

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

### How to change the frequency

1. Edit `src/config/config.yaml`:

```yaml
sources:
  binance:
    historical:
      interval: 5m   # e.g. switch from 1m to 5m
```

2. Restart or wait for the Airflow scheduler to re-parse DAGs.

3. No Python/DAG code changes are required.

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

---

## Manual trigger

1. Open Airflow UI: `http://localhost:8080` (default admin credentials from `docker/.env`).
2. Find DAG `incremental_market_data`.
3. Unpause if needed.
4. Trigger → “Trigger DAG”.
5. Confirm tasks: `start` → `run_bronze_pipeline` → `run_dbt_build` → `finish` all succeed.

CLI alternative:

```bash
docker exec market_data_airflow_scheduler \
  airflow dags trigger incremental_market_data

docker exec market_data_airflow_scheduler \
  airflow dags list-runs -d incremental_market_data
```

---

## Design decisions

| Decision | Rationale |
|----------|-----------|
| TaskFlow + EmptyOperator | Clear task names and typed task bodies |
| `retries=1`, `retry_delay=2m` | Tolerate transient Binance/DB blips without long backfills |
| `max_active_runs=1` | Prevent concurrent merges on incremental tables |
| Logging (not print) | Airflow task logs only |
| Cron utility in `src/common` | Reusable by future Bootstrap/maintenance DAGs |
