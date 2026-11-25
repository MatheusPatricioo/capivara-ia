"""Opens the capybara's long-term memory. Shared by the chat and by the autonomous mode."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import psycopg

from src.domain.discovery_memory import DiscoveryMemory
from src.domain.text_embedding import TextEmbedder
from src.infrastructure.memory_database import apply_schema
from src.infrastructure.ollama_text_embedder import OllamaTextEmbedder
from src.infrastructure.postgres_discovery_memory import (
    MemoryPool,
    PostgresDiscoveryMemory,
    SearchMode,
    create_memory_pool,
)
from src.infrastructure.settings import Settings
from src.infrastructure.task_prefixed_embedder import (
    NOMIC_DOCUMENT_PREFIX,
    NOMIC_QUERY_PREFIX,
    TaskPrefixedEmbedder,
)

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
    The schema files are applied first, so a database created before a new file
    (like the chunks table) gets it without being recreated.
    """
    _apply_schema_if_online(settings)
    pool = create_memory_pool(settings.memory_db_conninfo(), settings.memory_db_timeout_seconds)
    pool.open()
    logger.info(
        "Long-term memory: PostgreSQL at %s:%s/%s (%s search)",
        settings.memory_db_host,
        settings.memory_db_port,
        settings.memory_db_name,
        settings.memory_search_mode.value,
    )
    try:
        embedder = OllamaTextEmbedder(http_client, settings.ollama_embedding_model)
        yield build_discovery_memory(
            pool,
            embedder,
            task_prefixes=settings.memory_task_prefixes,
            search_mode=settings.memory_search_mode,
        )
    finally:
        pool.close(timeout=POOL_CLOSE_TIMEOUT_SECONDS)


def build_discovery_memory(
    pool: MemoryPool, embedder: TextEmbedder, task_prefixes: bool, search_mode: SearchMode
) -> PostgresDiscoveryMemory:
    """With task_prefixes, stored texts and searches get nomic-embed-text's task prefixes.

    Changing task_prefixes changes every embedding: run load_discoveries_into_memory after
    it, so the saved discoveries are embedded again the same way as the searches.
    """
    if not task_prefixes:
        return PostgresDiscoveryMemory(pool, embedder, search_mode=search_mode)
    return PostgresDiscoveryMemory(
        pool,
        TaskPrefixedEmbedder(embedder, NOMIC_DOCUMENT_PREFIX),
        query_embedder=TaskPrefixedEmbedder(embedder, NOMIC_QUERY_PREFIX),
        search_mode=search_mode,
    )


def _apply_schema_if_online(settings: Settings) -> None:
    try:
        apply_schema(settings)
    except psycopg.Error as error:
        logger.warning("Could not apply the memory schema (database offline?): %s", error)
