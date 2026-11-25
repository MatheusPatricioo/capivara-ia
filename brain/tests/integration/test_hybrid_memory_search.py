"""What the hybrid search adds over the vector search, against the real PostgreSQL."""

from collections.abc import Sequence
from datetime import date

import pytest

from src.domain.discovery import Discovery
from src.domain.text_embedding import Embedding
from src.infrastructure.postgres_discovery_memory import (
    EMBEDDING_DIMENSIONS,
    MemoryPool,
    PostgresDiscoveryMemory,
    SearchMode,
)
from tests.fakes.in_memory_discovery_memory import WordCountEmbedder, ZeroPaddedEmbedder

pytestmark = pytest.mark.database

# The fake embedder only knows these words: anything else is invisible to "meaning".
VOCABULARY = ("lua", "fases", "capivaras")


def make_discovery(title: str, summary: str) -> Discovery:
    return Discovery(title, "natureza", summary, ("https://example.com",), date(2026, 11, 24))


MOON = make_discovery("Fases da lua", "A lua tem fases.")
VICTORIA = make_discovery(
    "Vitória-régia", "Uma planta da Amazônia. As folhas aguentam peso. Ela flutua no rio."
)


class RecordingEmbedder:
    def __init__(self) -> None:
        self.received_texts: list[str] = []
        self._embedder = ZeroPaddedEmbedder(WordCountEmbedder(VOCABULARY), EMBEDDING_DIMENSIONS)

    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        self.received_texts.extend(texts)
        return self._embedder.embed(texts)


def build_memory(pool: MemoryPool, mode: SearchMode) -> PostgresDiscoveryMemory:
    embedder = ZeroPaddedEmbedder(WordCountEmbedder(VOCABULARY), EMBEDDING_DIMENSIONS)
    return PostgresDiscoveryMemory(pool, embedder, search_mode=mode)


def count_chunks(pool: MemoryPool) -> int:
    with pool.connection() as connection:
        row = connection.execute("SELECT count(*) FROM discovery_chunks").fetchone()
    assert row is not None
    return int(row[0])


def test_words_find_a_discovery_the_embedding_cannot_see(empty_memory_pool: MemoryPool) -> None:
    memory = build_memory(empty_memory_pool, SearchMode.HYBRID)
    memory.remember("lua.md", MOON)
    memory.remember("vitoria.md", VICTORIA)

    remembered = memory.recall("folhas que flutuam", limit=1)

    assert remembered[0].discovery == VICTORIA


def test_accents_do_not_matter_to_the_word_search(empty_memory_pool: MemoryPool) -> None:
    memory = build_memory(empty_memory_pool, SearchMode.HYBRID)
    memory.remember("lua.md", MOON)
    memory.remember("vitoria.md", VICTORIA)

    remembered = memory.recall("vitoria regia amazonia", limit=1)

    assert remembered[0].discovery == VICTORIA


def test_remember_stores_the_whole_text_and_the_sentence_windows(
    empty_memory_pool: MemoryPool,
) -> None:
    build_memory(empty_memory_pool, SearchMode.HYBRID).remember("vitoria.md", VICTORIA)

    assert count_chunks(empty_memory_pool) == 3


def test_remembering_again_replaces_the_old_chunks(empty_memory_pool: MemoryPool) -> None:
    memory = build_memory(empty_memory_pool, SearchMode.HYBRID)
    memory.remember("vitoria.md", VICTORIA)

    memory.remember("vitoria.md", MOON)

    assert count_chunks(empty_memory_pool) == 1


def test_searches_use_the_query_embedder(empty_memory_pool: MemoryPool) -> None:
    query_embedder = RecordingEmbedder()
    memory = PostgresDiscoveryMemory(
        empty_memory_pool,
        ZeroPaddedEmbedder(WordCountEmbedder(VOCABULARY), EMBEDDING_DIMENSIONS),
        query_embedder=query_embedder,
    )

    memory.recall("fases da lua", limit=1)

    assert query_embedder.received_texts == ["fases da lua"]
