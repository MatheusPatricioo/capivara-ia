"""Opens the capybara's long-term memory. Shared by the chat and by the autonomous mode."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import httpx

from src.domain.discovery_memory import DiscoveryMemory
from src.infrastructure.ollama_text_embedder import OllamaTextEmbedder
from src.infrastructure.postgres_discovery_memory import (
    PostgresDiscoveryMemory,
    create_memory_pool,
)
from src.infrastructure.settings import Settings

# When the database is offline, the pool threads are still retrying on exit; waiting
# longer for them would only delay closing the program.
POOL_CLOSE_TIMEOUT_SECONDS = 1.0

logger = logging.getLogger(__name__)


@contextmanager
def open_long_term_memory(
    settings: Settings, http_client: httpx.Client
) -> Iterator[DiscoveryMemory]:
    """The pgvector memory, with its connections closed when the `with` block ends.

    Opening never fails: with the database offline, each memory call fails after
    MEMORY_DB_TIMEOUT_SECONDS instead, and the callers decide what that means.
    """
    pool = create_memory_pool(settings.memory_db_conninfo(), settings.memory_db_timeout_seconds)
    pool.open()
    logger.info(
        "Long-term memory: PostgreSQL at %s:%s/%s",
        settings.memory_db_host,
        settings.memory_db_port,
        settings.memory_db_name,
    )
    try:
        embedder = OllamaTextEmbedder(http_client, settings.ollama_embedding_model)
        yield PostgresDiscoveryMemory(pool, embedder)
    finally:
        pool.close(timeout=POOL_CLOSE_TIMEOUT_SECONDS)
