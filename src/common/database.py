from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg
import yaml

from src.config.settings import Settings


class Database:
    """Creates PostgreSQL connections from the project configuration."""

    def __init__(
        self,
        settings: Settings | None = None,
        compose_path: str | Path | None = None,
        env_path: str | Path | None = None,
    ) -> None:
        self._settings = settings or Settings()
        project_root = Path(__file__).resolve().parents[2]
        self._compose_path = Path(compose_path) if compose_path else project_root / "docker-compose.yml"
        self._env_path = Path(env_path) if env_path else project_root / "docker/.env"
        self._compose_config = self._load_compose_config()
        self._env_config = self._load_env_config()

    def get_connection(self) -> psycopg.Connection[Any]:
        """Return a PostgreSQL connection to the warehouse database."""
        database_config = self._settings.database or {}
        dbname = database_config.get(
            "dbname",
            database_config.get("name", self._env_config["WAREHOUSE_DB"]),
        )

        # WAREHOUSE_* env vars allow Airflow containers to reach postgres
        # on the Docker network (host=postgres, port=5432) without changing
        # local host defaults (localhost:5433).
        host = os.environ.get(
            "WAREHOUSE_HOST",
            database_config.get("host", "localhost"),
        )
        port = int(
            os.environ.get(
                "WAREHOUSE_PORT",
                str(database_config.get("port", self._get_postgres_port())),
            )
        )

        return psycopg.connect(
            host=host,
            port=port,
            user=database_config.get("user", self._env_config["POSTGRES_USER"]),
            password=database_config.get(
                "password",
                self._env_config["POSTGRES_PASSWORD"],
            ),
            dbname=dbname,
        )

    def _load_compose_config(self) -> dict[str, Any]:
        with self._compose_path.open("r", encoding="utf-8") as compose_file:
            return yaml.safe_load(compose_file) or {}

    def _load_env_config(self) -> dict[str, str]:
        env_config: dict[str, str] = {}

        with self._env_path.open("r", encoding="utf-8") as env_file:
            for line in env_file:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith("#"):
                    continue

                key, _, value = stripped_line.partition("=")
                env_config[key.strip()] = value.strip()

        return env_config

    def _get_postgres_port(self) -> int:
        postgres_service = self._compose_config.get("services", {}).get("postgres", {})
        port_mapping = postgres_service.get("ports", [])[0]
        host_port = str(port_mapping).split(":", maxsplit=1)[0]
        return int(host_port.strip('"'))