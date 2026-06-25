# Market Data Pipeline

Infraestructura base local para un proyecto ELT con PostgreSQL + Airflow bajo arquitectura medallion.

## Componentes

- PostgreSQL 16 como data warehouse y metadata DB de Airflow
- Apache Airflow 2.9.3 con `LocalExecutor`
- Inicialización automática de la base con esquemas `bronze`, `silver` y `gold`
- Configuración por `env_file` para evitar credenciales hardcodeadas en `docker-compose.yml`

## Estructura relevante

- `docker-compose.yml`
- `docker/local_variables.example`
- `docker/postgres/init/01_init_databases.sh`
- `airflow/dags/`

## Cómo levantar el entorno

1. Copia el archivo de variables local:
   - `cp docker/local_variables.example docker/local_variables`
2. Levanta los servicios:
   - `docker compose up`

## Accesos

- Airflow UI: `http://localhost:8080`
- PostgreSQL: `localhost:5433`

## Credenciales por defecto

Las credenciales locales viven en `docker/local_variables`.

## Notas

- El volumen `postgres_data` persiste la información de PostgreSQL.
- Los scripts de inicialización se ejecutan desde `docker/postgres/init/`.
- `airflow/dags/` se monta en `/opt/airflow/dags`.
- Esta tarea no incluye lógica ETL ni DAGs complejos todavía.
