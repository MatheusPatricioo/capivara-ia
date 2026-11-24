import logging
from datetime import date

import pytest

from src.application.related_discoveries import RelatedDiscoveries
from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemoryError, RememberedDiscovery

MIN_SIMILARITY = 0.70
LILIES = "vitórias-régias boiando no laguinho"
MUSHROOMS = "cogumelos de chapéu vermelho"
WATERFALL = "uma cachoeira do outro lado da cerca"
RELATED_DISCOVERIES_LOGGER = "src.application.related_discoveries"


def make_discovery(title: str) -> Discovery:
    return Discovery(
        title=title,
        topic="natureza",
        summary=f"Resumo sobre {title}",
        sources=("https://example.com",),
        discovered_on=date(2026, 11, 24),
    )


VICTORIA = make_discovery("Vitória-régia")
AMANITA = make_discovery("Cogumelo mata-moscas")


class ScriptedMemory:
    """Answers each subject with a fixed recall and remembers what it was asked."""

    def __init__(self, answers: dict[str, list[RememberedDiscovery]]) -> None:
        self._answers = answers
        self.recalled_subjects: list[str] = []

    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise AssertionError("related discoveries must only recall")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        self.recalled_subjects.append(text)
        return self._answers.get(text, [])[:limit]


class OfflineMemory:
    def __init__(self) -> None:
        self.recall_attempts = 0

    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise DiscoveryMemoryError("database offline")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        self.recall_attempts += 1
        raise DiscoveryMemoryError("database offline")


@pytest.fixture
def memory() -> ScriptedMemory:
    return ScriptedMemory(
        {
            LILIES: [RememberedDiscovery(VICTORIA, 0.81), RememberedDiscovery(AMANITA, 0.75)],
            MUSHROOMS: [RememberedDiscovery(AMANITA, 0.77)],
            WATERFALL: [RememberedDiscovery(AMANITA, 0.66)],
        }
    )


@pytest.fixture
def related(memory: ScriptedMemory) -> RelatedDiscoveries:
    return RelatedDiscoveries(memory, MIN_SIMILARITY)


def test_brings_the_closest_discovery_of_each_subject(related: RelatedDiscoveries) -> None:
    assert related.about([LILIES, MUSHROOMS]) == [VICTORIA, AMANITA]


def test_brings_only_the_closest_discovery_even_when_the_second_is_above_the_threshold(
    related: RelatedDiscoveries,
) -> None:
    assert related.about([LILIES]) == [VICTORIA]


def test_leaves_out_a_closest_discovery_below_the_threshold(
    related: RelatedDiscoveries,
) -> None:
    assert related.about([WATERFALL]) == []


def test_brings_a_discovery_at_exactly_the_threshold() -> None:
    memory = ScriptedMemory({LILIES: [RememberedDiscovery(VICTORIA, MIN_SIMILARITY)]})

    assert RelatedDiscoveries(memory, MIN_SIMILARITY).about([LILIES]) == [VICTORIA]


def test_does_not_repeat_a_discovery_related_to_two_subjects() -> None:
    other_mushrooms = "um grupinho de cogumelos"
    memory = ScriptedMemory(
        {
            MUSHROOMS: [RememberedDiscovery(AMANITA, 0.77)],
            other_mushrooms: [RememberedDiscovery(AMANITA, 0.74)],
        }
    )

    assert RelatedDiscoveries(memory, MIN_SIMILARITY).about([MUSHROOMS, other_mushrooms]) == [
        AMANITA
    ]


def test_brings_nothing_when_the_memory_is_empty() -> None:
    assert RelatedDiscoveries(ScriptedMemory({}), MIN_SIMILARITY).about([LILIES]) == []


def test_recalls_one_discovery_per_subject(
    related: RelatedDiscoveries, memory: ScriptedMemory
) -> None:
    related.about([LILIES, WATERFALL])

    assert memory.recalled_subjects == [LILIES, WATERFALL]


def test_brings_nothing_when_the_memory_is_offline() -> None:
    assert RelatedDiscoveries(OfflineMemory(), MIN_SIMILARITY).about([LILIES]) == []


def test_stops_at_the_first_subject_when_the_memory_is_offline() -> None:
    memory = OfflineMemory()

    RelatedDiscoveries(memory, MIN_SIMILARITY).about([LILIES, MUSHROOMS, WATERFALL])

    assert memory.recall_attempts == 1


def test_logs_a_warning_when_the_memory_is_offline(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger=RELATED_DISCOVERIES_LOGGER)

    RelatedDiscoveries(OfflineMemory(), MIN_SIMILARITY).about([LILIES])

    assert caplog.messages == ["Could not recall related discoveries: database offline"]


def test_logs_every_comparison_for_recalibration(
    related: RelatedDiscoveries, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=RELATED_DISCOVERIES_LOGGER)

    related.about([LILIES, WATERFALL])

    assert caplog.messages == [
        f"Closest memory to '{LILIES}': 'Vitória-régia' (0.810, related)",
        f"Closest memory to '{WATERFALL}': 'Cogumelo mata-moscas' (0.660, below the threshold)",
    ]
