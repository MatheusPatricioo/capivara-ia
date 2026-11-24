"""Shared fixtures for tests that need the real PostgreSQL from compose.yaml.

They use a separate database, "<MEMORY_DB_NAME>_test", created on demand with the same
schema file Docker runs, so tests never touch the capybara's real memory. When the
database is offline, those tests are skipped (not failed) with a hint on how to start it.
"""

from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql

from src.infrastructure.postgres_discovery_memory import MemoryPool, create_memory_pool
from src.infrastructure.settings import PROJECT_ROOT, Settings

SCHEMA_FILE = PROJECT_ROOT / "brain" / "database" / "init" / "001_create_discoveries.sql"
MAINTENANCE_DATABASE = "postgres"
CONNECT_TIMEOUT_SECONDS = 3
OFFLINE_HINT = "PostgreSQL is offline; start it with: docker compose --env-file brain/.env up -d"


def _with_database(settings: Settings, database: str) -> Settings:
    return settings.model_copy(update={"memory_db_name": database})


def _create_database_if_missing(settings: Settings) -> None:
    # CREATE DATABASE cannot run inside a transaction, hence autocommit.
    maintenance_settings = _with_database(settings, MAINTENANCE_DATABASE)
    with psycopg.connect(
        maintenance_settings.memory_db_conninfo(),
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    ) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (settings.memory_db_name,)
        ).fetchone()
        if exists is None:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(settings.memory_db_name))
            )


def _apply_schema(settings: Settings) -> None:
    # The schema file only uses IF NOT EXISTS, so applying it on every run is harmless.
    with psycopg.connect(
        settings.memory_db_conninfo(), connect_timeout=CONNECT_TIMEOUT_SECONDS
    ) as connection:
        connection.execute(SCHEMA_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def memory_test_settings() -> Settings:
    """brain/.env settings pointing at the test database, created and migrated on demand."""
    settings = Settings()
    test_settings = _with_database(settings, f"{settings.memory_db_name}_test")
    try:
        _create_database_if_missing(test_settings)
    except psycopg.OperationalError:
        pytest.skip(OFFLINE_HINT)
    _apply_schema(test_settings)
    return test_settings


@pytest.fixture(scope="session")
def memory_test_pool(memory_test_settings: Settings) -> Iterator[MemoryPool]:
    with create_memory_pool(
        memory_test_settings.memory_db_conninfo(),
        memory_test_settings.memory_db_timeout_seconds,
    ) as pool:
        yield pool


@pytest.fixture
def empty_memory_pool(memory_test_pool: MemoryPool) -> MemoryPool:
    """The test pool with the discoveries table emptied, so each test starts clean."""
    with memory_test_pool.connection() as connection:
        connection.execute("TRUNCATE discoveries")
    return memory_test_pool
