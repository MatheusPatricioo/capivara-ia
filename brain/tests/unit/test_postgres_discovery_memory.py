"""What the pgvector adapter adds on top of the contract: its helpers and its errors.

The error tests use a pool pointing at a closed port, so they run without the database.
"""

from collections.abc import Iterator, Sequence
from datetime import date

import pytest
from psycopg.conninfo import conninfo_to_dict

from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemoryError
from src.domain.text_embedding import Embedding, EmbeddingError
from src.infrastructure.postgres_discovery_memory import (
    EMBEDDING_DIMENSIONS,
    MemoryPool,
    PostgresDiscoveryMemory,
    create_memory_pool,
    memory_conninfo,
    to_vector_literal,
)

# Port 1 is never a PostgreSQL server, so every connection attempt is refused.
OFFLINE_CONNINFO = memory_conninfo("127.0.0.1", 1, "capybara_memory", "capybara", "secret")
OFFLINE_POOL_TIMEOUT_SECONDS = 0.5

MOON = Discovery(
    title="Fases da lua",
    topic="lua",
    summary="A lua tem fases",
    sources=("https://example.com/lua",),
    discovered_on=date(2026, 11, 24),
)


class ConstantEmbedder:
    """Fake embedder: the same vector for any text."""

    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        return [(1.0,) * self._dimensions for _ in texts]


class FailingEmbedder:
    """Fake embedder that behaves like Ollama being offline."""

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        raise EmbeddingError("Ollama is offline")


@pytest.fixture
def offline_pool() -> Iterator[MemoryPool]:
    pool = create_memory_pool(OFFLINE_CONNINFO, OFFLINE_POOL_TIMEOUT_SECONDS)
    pool.open()
    yield pool
    # Its threads are still retrying the closed port; there is nothing to wait for.
    pool.close(timeout=0)


@pytest.fixture
def unopened_pool() -> MemoryPool:
    """Never opened: enough when the embedder fails before any connection is asked for."""
    return create_memory_pool(OFFLINE_CONNINFO, OFFLINE_POOL_TIMEOUT_SECONDS)


@pytest.fixture
def memory_without_database(offline_pool: MemoryPool) -> PostgresDiscoveryMemory:
    return PostgresDiscoveryMemory(offline_pool, ConstantEmbedder(EMBEDDING_DIMENSIONS))


@pytest.fixture
def memory_without_embedder(unopened_pool: MemoryPool) -> PostgresDiscoveryMemory:
    return PostgresDiscoveryMemory(unopened_pool, FailingEmbedder())


def test_to_vector_literal_writes_the_pgvector_text_format() -> None:
    embedding = (0.5, -1.0) + (0.0,) * (EMBEDDING_DIMENSIONS - 2)

    literal = to_vector_literal(embedding)

    assert literal.startswith("[0.5,-1.0,0.0,")


def test_to_vector_literal_rejects_an_embedding_of_another_size() -> None:
    with pytest.raises(DiscoveryMemoryError, match=f"stores {EMBEDDING_DIMENSIONS}"):
        to_vector_literal((0.1, 0.2, 0.3))


def test_memory_conninfo_keeps_a_password_with_spaces_intact() -> None:
    conninfo = memory_conninfo("127.0.0.1", 5432, "capybara_memory", "capybara", "my secret")

    assert conninfo_to_dict(conninfo)["password"] == "my secret"


def test_remember_raises_memory_error_when_the_database_is_offline(
    memory_without_database: PostgresDiscoveryMemory,
) -> None:
    with pytest.raises(DiscoveryMemoryError, match="Could not remember fases-da-lua.md"):
        memory_without_database.remember("fases-da-lua.md", MOON)


def test_recall_raises_memory_error_when_the_database_is_offline(
    memory_without_database: PostgresDiscoveryMemory,
) -> None:
    with pytest.raises(DiscoveryMemoryError, match="Could not recall"):
        memory_without_database.recall("lua", limit=3)


def test_remember_raises_memory_error_when_the_embedder_fails(
    memory_without_embedder: PostgresDiscoveryMemory,
) -> None:
    with pytest.raises(DiscoveryMemoryError, match="Ollama is offline"):
        memory_without_embedder.remember("fases-da-lua.md", MOON)


def test_recall_raises_memory_error_when_the_embedder_fails(
    memory_without_embedder: PostgresDiscoveryMemory,
) -> None:
    with pytest.raises(DiscoveryMemoryError, match="Ollama is offline"):
        memory_without_embedder.recall("lua", limit=3)
