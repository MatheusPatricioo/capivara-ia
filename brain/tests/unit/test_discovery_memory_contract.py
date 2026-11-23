"""Contract of DiscoveryMemory: every implementation must pass these same tests.

The `memory` fixture is parametrized: today only the in-memory fake; the pgvector
adapter joins it, so the fake used elsewhere is proven to behave like the database.
"""

from datetime import date

import pytest

from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemory
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder

VOCABULARY = ("lua", "fases", "estrelas", "constelações", "capivaras", "grupos")


def make_discovery(title: str, topic: str, summary: str) -> Discovery:
    return Discovery(
        title=title,
        topic=topic,
        summary=summary,
        sources=("https://example.com/page",),
        discovered_on=date(2026, 11, 23),
    )


MOON = make_discovery("Fases da lua", "lua", "A lua tem fases")
STARS = make_discovery("Constelações", "estrelas", "Estrelas formam constelações")
CAPYBARAS = make_discovery("Capivaras em grupos", "capivaras", "Capivaras vivem em grupos")


@pytest.fixture(params=["in_memory"])
def memory(request: pytest.FixtureRequest) -> DiscoveryMemory:
    return InMemoryDiscoveryMemory(WordCountEmbedder(VOCABULARY))


@pytest.fixture
def memory_with_three_discoveries(memory: DiscoveryMemory) -> DiscoveryMemory:
    memory.remember("fases-da-lua.md", MOON)
    memory.remember("constelacoes.md", STARS)
    memory.remember("capivaras-em-grupos.md", CAPYBARAS)
    return memory


def test_recall_on_an_empty_memory_returns_nothing(memory: DiscoveryMemory) -> None:
    assert memory.recall("fases da lua", limit=3) == []


def test_recall_brings_the_closest_discovery_first(
    memory_with_three_discoveries: DiscoveryMemory,
) -> None:
    remembered = memory_with_three_discoveries.recall("as fases da lua", limit=3)

    assert remembered[0].discovery == MOON


def test_recall_orders_discoveries_from_most_to_least_similar(
    memory_with_three_discoveries: DiscoveryMemory,
) -> None:
    remembered = memory_with_three_discoveries.recall("estrelas e lua", limit=3)

    similarities = [memory.similarity for memory in remembered]
    assert similarities == sorted(similarities, reverse=True)


def test_recall_returns_at_most_the_limit(
    memory_with_three_discoveries: DiscoveryMemory,
) -> None:
    remembered = memory_with_three_discoveries.recall("lua", limit=2)

    assert len(remembered) == 2


def test_recall_of_the_same_text_has_similarity_close_to_one(memory: DiscoveryMemory) -> None:
    memory.remember("fases-da-lua.md", MOON)

    [remembered] = memory.recall("Fases da lua\nlua\nA lua tem fases", limit=1)

    assert remembered.similarity == pytest.approx(1.0)


def test_remembering_the_same_file_again_replaces_the_old_discovery(
    memory: DiscoveryMemory,
) -> None:
    updated_moon = make_discovery("Fases da lua", "lua", "A lua tem quatro fases principais")
    memory.remember("fases-da-lua.md", MOON)
    memory.remember("fases-da-lua.md", updated_moon)

    remembered = memory.recall("lua", limit=5)

    assert [memory.discovery for memory in remembered] == [updated_moon]
