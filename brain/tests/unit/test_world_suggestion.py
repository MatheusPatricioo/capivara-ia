from dataclasses import replace
from datetime import date

import pytest

from src.domain.world_suggestion import (
    MAX_REQUEST_LENGTH,
    InvalidSuggestionError,
    WorldSuggestion,
)

SUGGESTION = WorldSuggestion(
    request="Um laguinho com vitórias-régias",
    reason="Aprendi que as folhas delas aguentam o peso de uma criança!",
    inspired_by="Vitórias-régias gigantes",
    suggested_on=date(2026, 11, 24),
)


def test_keeps_a_valid_suggestion_as_it_was_given() -> None:
    assert SUGGESTION.request == "Um laguinho com vitórias-régias"


def test_rejects_a_blank_request() -> None:
    with pytest.raises(InvalidSuggestionError, match="needs a request"):
        replace(SUGGESTION, request="   ")


def test_rejects_a_request_longer_than_a_title() -> None:
    with pytest.raises(InvalidSuggestionError, match="like a title"):
        replace(SUGGESTION, request="a" * (MAX_REQUEST_LENGTH + 1))


def test_accepts_a_request_at_the_length_limit() -> None:
    suggestion = replace(SUGGESTION, request="a" * MAX_REQUEST_LENGTH)

    assert len(suggestion.request) == MAX_REQUEST_LENGTH


def test_rejects_a_blank_reason() -> None:
    with pytest.raises(InvalidSuggestionError, match="needs a reason"):
        replace(SUGGESTION, reason="")


def test_rejects_a_suggestion_without_the_discovery_that_inspired_it() -> None:
    with pytest.raises(InvalidSuggestionError, match="discovery that inspired it"):
        replace(SUGGESTION, inspired_by=" ")
