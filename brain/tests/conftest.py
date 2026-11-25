"""Shared fixtures for tests that need the real PostgreSQL from compose.yaml.

They use a separate database, "<MEMORY_DB_NAME>_test", created on demand with the same
schema file Docker runs, so tests never touch the capybara's real memory. When the
database is offline, those tests are skipped (not failed) with a hint on how to start it.
"""

from collections.abc import Iterator

import psycopg
import pytest

from src.infrastructure.memory_database import prepare_side_database
from src.infrastructure.postgres_discovery_memory import MemoryPool, create_memory_pool
from src.infrastructure.settings import Settings

TEST_DATABASE_SUFFIX = "test"
OFFLINE_HINT = "PostgreSQL is offline; start it with: docker compose --env-file brain/.env up -d"


@pytest.fixture(scope="session")
def memory_test_settings() -> Settings:
    """brain/.env settings pointing at the test database, created and migrated on demand."""
    try:
        return prepare_side_database(Settings(), TEST_DATABASE_SUFFIX)
    except psycopg.OperationalError:
        pytest.skip(OFFLINE_HINT)


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
