"""open_long_term_memory wires the pool, the Ollama embedder and the pgvector adapter.

Ollama is replaced by httpx.MockTransport (never a real model in tests); the database
is the test one from conftest.py, or an unreachable port for the offline case.
"""

import json
from datetime import date

import httpx
import pytest

from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemoryError
from src.infrastructure.postgres_discovery_memory import EMBEDDING_DIMENSIONS, MemoryPool
from src.infrastructure.settings import Settings
from src.long_term_memory import open_long_term_memory

MOON = Discovery(
    title="Fases da lua",
    topic="lua",
    summary="A lua tem fases",
    sources=("https://example.com/lua",),
    discovered_on=date(2026, 11, 24),
)


def same_embedding_for_every_text(request: httpx.Request) -> httpx.Response:
    """Fake Ollama /api/embed: one fixed 768-number vector per input text."""
    input_count = len(json.loads(request.content)["input"])
    return httpx.Response(200, json={"embeddings": [[1.0] * EMBEDDING_DIMENSIONS] * input_count})


@pytest.fixture
def fake_ollama() -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(same_embedding_for_every_text), base_url="http://ollama"
    )


@pytest.fixture
def offline_settings() -> Settings:
    # Port 1 is never a PostgreSQL server; a short timeout keeps the test quick.
    return Settings(_env_file=None, memory_db_port=1, memory_db_timeout_seconds=0.5)


@pytest.mark.database
def test_the_opened_memory_remembers_and_recalls_from_postgres(
    memory_test_settings: Settings, empty_memory_pool: MemoryPool, fake_ollama: httpx.Client
) -> None:
    with open_long_term_memory(memory_test_settings, fake_ollama) as memory:
        memory.remember("fases-da-lua.md", MOON)
        [remembered] = memory.recall("lua", limit=1)

    assert remembered.discovery == MOON


def test_remembering_fails_with_a_memory_error_when_the_database_is_offline(
    offline_settings: Settings, fake_ollama: httpx.Client
) -> None:
    with (
        open_long_term_memory(offline_settings, fake_ollama) as memory,
        pytest.raises(DiscoveryMemoryError),
    ):
        memory.remember("fases-da-lua.md", MOON)
