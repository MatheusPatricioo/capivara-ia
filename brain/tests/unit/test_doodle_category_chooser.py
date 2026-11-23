import logging
from datetime import date

import pytest

from src.application.category_matcher import CategoryCandidate
from src.application.doodle_category_chooser import (
    NONE_OF_THEM,
    DoodleCategoryChooser,
    choice_schema,
)
from src.domain.discovery import Discovery
from src.domain.language_model import ChatMessage, Role, StructuredReply

CHOOSER_LOGGER = "src.application.doodle_category_chooser"
INSTRUCTIONS_TEMPLATE = "Escolha um rascunho:\n{candidates}"
SUNFLOWERS = Discovery(
    title="Girassóis seguem o Sol",
    topic="plantas",
    summary="Girassóis jovens viram a cabeça acompanhando o Sol.",
    sources=("https://example.com/girassol",),
    discovered_on=date(2026, 11, 23),
)
CANDIDATES = (
    CategoryCandidate(category="sun", label="sol", similarity=0.635),
    CategoryCandidate(category="flower", label="flor, flores", similarity=0.626),
    CategoryCandidate(category="house plant", label="planta de vaso", similarity=0.612),
)


class FixedCandidateFinder:
    """Stands in for the embeddings: always the same candidates, and records the request."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, int]] = []

    def candidates(self, text: str, count: int) -> tuple[CategoryCandidate, ...]:
        self.requests.append((text, count))
        return CANDIDATES


class ScriptedLanguageModel:
    """Answers with a fixed JSON and records what it was asked."""

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data
        self.received_messages: list[list[ChatMessage]] = []
        self.received_schemas: list[dict[str, object]] = []

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        self.received_messages.append(messages)
        self.received_schemas.append(schema)
        return StructuredReply(data=self._data)


@pytest.fixture
def finder() -> FixedCandidateFinder:
    return FixedCandidateFinder()


@pytest.fixture
def model_choosing_the_flower() -> ScriptedLanguageModel:
    return ScriptedLanguageModel({"category": "flower"})


def chooser_with(
    language_model: ScriptedLanguageModel, finder: FixedCandidateFinder
) -> DoodleCategoryChooser:
    return DoodleCategoryChooser(finder, language_model, INSTRUCTIONS_TEMPLATE, candidate_count=3)


def test_returns_the_candidate_the_model_chose(
    model_choosing_the_flower: ScriptedLanguageModel, finder: FixedCandidateFinder
) -> None:
    """The model may pick a candidate that is not the closest one: that is the rerank."""
    assert chooser_with(model_choosing_the_flower, finder).choose(SUNFLOWERS) == "flower"


def test_retrieves_candidates_by_the_title_and_the_summary(
    model_choosing_the_flower: ScriptedLanguageModel, finder: FixedCandidateFinder
) -> None:
    chooser_with(model_choosing_the_flower, finder).choose(SUNFLOWERS)

    assert finder.requests == [
        ("Girassóis seguem o Sol. Girassóis jovens viram a cabeça acompanhando o Sol.", 3)
    ]


def test_returns_none_when_the_model_says_none_of_them(finder: FixedCandidateFinder) -> None:
    chooser = chooser_with(ScriptedLanguageModel({"category": NONE_OF_THEM}), finder)

    assert chooser.choose(SUNFLOWERS) is None


def test_refuses_a_category_that_was_not_offered(finder: FixedCandidateFinder) -> None:
    chooser = chooser_with(ScriptedLanguageModel({"category": "cat"}), finder)

    assert chooser.choose(SUNFLOWERS) is None


def test_refuses_an_answer_without_a_category(finder: FixedCandidateFinder) -> None:
    chooser = chooser_with(ScriptedLanguageModel({"choice": "flower"}), finder)

    assert chooser.choose(SUNFLOWERS) is None


def test_lets_the_model_answer_only_a_candidate_or_none(
    model_choosing_the_flower: ScriptedLanguageModel, finder: FixedCandidateFinder
) -> None:
    chooser_with(model_choosing_the_flower, finder).choose(SUNFLOWERS)

    assert model_choosing_the_flower.received_schemas == [
        choice_schema(["sun", "flower", "house plant"])
    ]


def test_the_schema_offers_none_of_them_as_an_option() -> None:
    schema_properties = choice_schema(["sun"])["properties"]

    assert schema_properties == {"category": {"type": "string", "enum": ["sun", NONE_OF_THEM]}}


def test_shows_the_candidates_with_their_labels_and_the_discovery_as_data(
    model_choosing_the_flower: ScriptedLanguageModel, finder: FixedCandidateFinder
) -> None:
    chooser_with(model_choosing_the_flower, finder).choose(SUNFLOWERS)

    assert model_choosing_the_flower.received_messages == [
        [
            ChatMessage(
                Role.SYSTEM,
                "Escolha um rascunho:\n- sun: sol\n- flower: flor, flores\n"
                "- house plant: planta de vaso",
            ),
            ChatMessage(
                Role.USER,
                "Título: Girassóis seguem o Sol\n"
                "Resumo: Girassóis jovens viram a cabeça acompanhando o Sol.",
            ),
        ]
    ]


def test_logs_the_candidates_with_their_similarity_and_the_choice(
    model_choosing_the_flower: ScriptedLanguageModel,
    finder: FixedCandidateFinder,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=CHOOSER_LOGGER)

    chooser_with(model_choosing_the_flower, finder).choose(SUNFLOWERS)

    assert caplog.messages == [
        "Doodle candidates for 'Girassóis seguem o Sol': "
        "sun 0.635, flower 0.626, house plant 0.612; chose 'flower'"
    ]


def test_warns_about_a_choice_outside_the_options(
    finder: FixedCandidateFinder, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=CHOOSER_LOGGER)

    chooser_with(ScriptedLanguageModel({"category": "cat"}), finder).choose(SUNFLOWERS)

    assert caplog.messages == ["Ignoring a doodle choice outside the options: 'cat'"]
