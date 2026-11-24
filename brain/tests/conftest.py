"""Shared fixtures for tests that need the real PostgreSQL from compose.yaml.

They use a separate database, "<MEMORY_DB_NAME>_test", created on demand with the same
schema file Docker runs, so tests never touch the capybara's real memory. When the
database is offline, those tests are skipped (not failed) with a hint on how to start it.
"""

from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql

from src.infrastructure.postgres_discovery_memory import (
    MemoryPool,
    create_memory_pool,
    memory_conninfo,
)
from src.infrastructure.settings import PROJECT_ROOT, Settings

SCHEMA_FILE = PROJECT_ROOT / "brain" / "database" / "init" / "001_create_discoveries.sql"
MAINTENANCE_DATABASE = "postgres"
CONNECT_TIMEOUT_SECONDS = 3
POOL_TIMEOUT_SECONDS = 5.0
OFFLINE_HINT = "PostgreSQL is offline; start it with: docker compose --env-file brain/.env up -d"


def _conninfo(settings: Settings, database: str) -> str:
    return memory_conninfo(
        host=settings.memory_db_host,
        port=settings.memory_db_port,
        database=database,
        user=settings.memory_db_user,
        password=settings.memory_db_password.get_secret_value(),
    )


def _create_database_if_missing(settings: Settings, database: str) -> None:
    # CREATE DATABASE cannot run inside a transaction, hence autocommit.
    with psycopg.connect(
        _conninfo(settings, MAINTENANCE_DATABASE),
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    ) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (database,)
        ).fetchone()
        if exists is None:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))


def _apply_schema(conninfo: str) -> None:
    # The schema file only uses IF NOT EXISTS, so applying it on every run is harmless.
    with psycopg.connect(conninfo, connect_timeout=CONNECT_TIMEOUT_SECONDS) as connection:
        connection.execute(SCHEMA_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def memory_test_pool() -> Iterator[MemoryPool]:
    settings = Settings()
    test_database = f"{settings.memory_db_name}_test"
    try:
        _create_database_if_missing(settings, test_database)
    except psycopg.OperationalError:
        pytest.skip(OFFLINE_HINT)
    conninfo = _conninfo(settings, test_database)
    _apply_schema(conninfo)
    with create_memory_pool(conninfo, POOL_TIMEOUT_SECONDS) as pool:
        yield pool


@pytest.fixture
def empty_memory_pool(memory_test_pool: MemoryPool) -> MemoryPool:
    """The test pool with the discoveries table emptied, so each test starts clean."""
    with memory_test_pool.connection() as connection:
        connection.execute("TRUNCATE discoveries")
    return memory_test_pool
