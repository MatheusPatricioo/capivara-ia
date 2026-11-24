import logging
from collections.abc import Sequence

import pytest

from src.application.repeated_suggestions import EarlierSuggestion, RepeatedSuggestions
from src.domain.text_embedding import Embedding, EmbeddingError
from tests.fakes.in_memory_discovery_memory import WordCountEmbedder
from tests.fakes.in_memory_suggestions import InMemorySuggestionArchive, a_suggestion

MIN_SIMILARITY = 0.80
VOCABULARY = ["laguinho", "vitórias-régias", "vaga-lumes", "jardim", "luneta", "noite"]
EARLIER_REQUESTS = ["Vaga-lumes no jardim", "Um laguinho com vitórias-régias"]
REPEATED_SUGGESTIONS_LOGGER = "src.application.repeated_suggestions"


def archive_with(requests: list[str]) -> InMemorySuggestionArchive:
    """An archive with one pending suggestion per request."""
    return InMemorySuggestionArchive([a_suggestion(request) for request in requests])


class OfflineEmbedder:
    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        raise EmbeddingError("Ollama is not running")


@pytest.fixture
def repeated_suggestions() -> RepeatedSuggestions:
    return RepeatedSuggestions(
        archive_with(EARLIER_REQUESTS), WordCountEmbedder(VOCABULARY), MIN_SIMILARITY
    )


def test_finds_an_earlier_suggestion_with_the_same_meaning(
    repeated_suggestions: RepeatedSuggestions,
) -> None:
    earlier = repeated_suggestions.earlier_version_of("Vitórias-régias no laguinho")

    assert earlier == EarlierSuggestion("Um laguinho com vitórias-régias", pytest.approx(1.0))


def test_finds_nothing_when_the_wish_is_new(repeated_suggestions: RepeatedSuggestions) -> None:
    assert repeated_suggestions.earlier_version_of("Uma luneta para a noite") is None


def test_finds_nothing_below_the_minimum_similarity(
    repeated_suggestions: RepeatedSuggestions,
) -> None:
    # Shares only "jardim" with "Vaga-lumes no jardim": similarity 1 / (√2 × √2) = 0.5.
    assert repeated_suggestions.earlier_version_of("Um jardim de noite") is None


def test_finds_nothing_when_there_are_no_earlier_suggestions() -> None:
    repeated_suggestions = RepeatedSuggestions(
        archive_with([]), OfflineEmbedder(), MIN_SIMILARITY
    )

    assert repeated_suggestions.earlier_version_of("Vaga-lumes no jardim") is None


def test_lets_an_embedding_error_reach_the_caller() -> None:
    repeated_suggestions = RepeatedSuggestions(
        archive_with(EARLIER_REQUESTS), OfflineEmbedder(), MIN_SIMILARITY
    )

    with pytest.raises(EmbeddingError):
        repeated_suggestions.earlier_version_of("Vaga-lumes no jardim")


def test_logs_the_closest_earlier_suggestion(
    repeated_suggestions: RepeatedSuggestions, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=REPEATED_SUGGESTIONS_LOGGER):
        repeated_suggestions.earlier_version_of("Uma luneta para a noite")

    assert "Closest earlier suggestion to 'Uma luneta para a noite'" in caplog.text
