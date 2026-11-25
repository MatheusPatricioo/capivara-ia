"""RelatedDiscoveries with query rewriting (expander) and rerank (chooser)."""

from datetime import date

import pytest

from src.application.memory_query_expander import MemoryQueryExpander
from src.application.related_discoveries import RelatedDiscoveries
from src.application.related_memory_chooser import RelatedMemoryChooser
from src.domain.discovery import Discovery
from src.domain.discovery_memory import RememberedDiscovery
from src.domain.language_model import ChatMessage, LanguageModelError, StructuredReply

SUBJECT = "luzinhas piscando no jardim"
EXPANDED = "luzinhas piscando no jardim vaga-lumes"
MIN_SIMILARITY = 0.5


def make_discovery(title: str) -> Discovery:
    return Discovery(
        title, "insetos", f"Resumo sobre {title}", ("https://e.com",), date(2026, 1, 1)
    )


FIREFLIES = make_discovery("Vaga-lumes")
BEES = make_discovery("Abelhas")
TOO_FAR = make_discovery("Vulcões")


class ScriptedMemory:
    def __init__(self, candidates: list[RememberedDiscovery]) -> None:
        self._candidates = candidates
        self.queries: list[str] = []

    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise AssertionError("only recall is expected")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        self.queries.append(text)
        return self._candidates[:limit]


class AnsweringModel:
    """Structured model that answers with fixed data and records what it was shown."""

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data
        self.received_messages: list[ChatMessage] = []

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        self.received_messages = messages
        return StructuredReply(self._data)


class OfflineModel:
    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        raise LanguageModelError("Ollama is offline")


@pytest.fixture
def memory() -> ScriptedMemory:
    return ScriptedMemory(
        [
            RememberedDiscovery(BEES, 0.71),
            RememberedDiscovery(FIREFLIES, 0.69),
            RememberedDiscovery(TOO_FAR, 0.30),
        ]
    )


def related_with(memory: ScriptedMemory, choice: str) -> RelatedDiscoveries:
    chooser = RelatedMemoryChooser(AnsweringModel({"choice": choice}), "{candidates}")
    return RelatedDiscoveries(memory, MIN_SIMILARITY, chooser=chooser)


def test_the_chooser_can_pick_a_candidate_that_is_not_the_closest(memory: ScriptedMemory) -> None:
    assert related_with(memory, "2").closest_to(SUBJECT) == FIREFLIES


def test_the_chooser_can_decide_that_no_candidate_is_about_the_subject(
    memory: ScriptedMemory,
) -> None:
    assert related_with(memory, "nenhuma").closest_to(SUBJECT) is None


def test_a_choice_outside_the_options_is_refused(memory: ScriptedMemory) -> None:
    assert related_with(memory, "7").closest_to(SUBJECT) is None


def test_candidates_below_the_minimum_similarity_are_not_offered(memory: ScriptedMemory) -> None:
    model = AnsweringModel({"choice": "nenhuma"})
    related = RelatedDiscoveries(
        memory, MIN_SIMILARITY, chooser=RelatedMemoryChooser(model, "{candidates}")
    )

    related.closest_to(SUBJECT)

    assert "Vulcões" not in model.received_messages[0].content


def test_an_offline_chooser_brings_back_nothing(memory: ScriptedMemory) -> None:
    related = RelatedDiscoveries(
        memory, MIN_SIMILARITY, chooser=RelatedMemoryChooser(OfflineModel(), "{candidates}")
    )

    assert related.closest_to(SUBJECT) is None


def test_the_rewritten_query_is_searched_with_the_subject(memory: ScriptedMemory) -> None:
    expander = MemoryQueryExpander(AnsweringModel({"query": "vaga-lumes"}), "Reescreva.")
    related = RelatedDiscoveries(memory, MIN_SIMILARITY, expander=expander)

    related.closest_to(SUBJECT)

    assert memory.queries == [EXPANDED]


def test_an_empty_rewrite_searches_the_subject_alone(memory: ScriptedMemory) -> None:
    expander = MemoryQueryExpander(AnsweringModel({"query": "  "}), "Reescreva.")
    related = RelatedDiscoveries(memory, MIN_SIMILARITY, expander=expander)

    related.closest_to(SUBJECT)

    assert memory.queries == [SUBJECT]


def test_an_offline_expander_searches_the_subject_alone(memory: ScriptedMemory) -> None:
    related = RelatedDiscoveries(
        memory, MIN_SIMILARITY, expander=MemoryQueryExpander(OfflineModel(), "Reescreva.")
    )

    related.closest_to(SUBJECT)

    assert memory.queries == [SUBJECT]
