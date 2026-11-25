from dataclasses import replace

import pytest

from src.application.feelings_voice import FeelingsVoice
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.emotional_life import EmotionalLife
from tests.fakes.emotional_lives import NOW, a_life
from tests.fakes.in_memory_suggestions import InMemorySuggestionArchive, a_suggestion

TEMPLATE = "(Por dentro:\n{feelings})"


class FixedHeart:
    """Always the same life; remembers how many wishes it was told were waiting."""

    def __init__(self, life: EmotionalLife) -> None:
        self._life = life
        self.told_pending_wishes: list[int | None] = []

    def check_in(self, pending_wishes: int | None = None) -> EmotionalLife:
        self.told_pending_wishes.append(pending_wishes)
        return self._life


@pytest.fixture
def heart() -> FixedHeart:
    return FixedHeart(a_life({Emotion.CURIOSITY: 0.8}))


def test_fills_the_template_with_how_she_feels(heart: FixedHeart) -> None:
    voice = FeelingsVoice(heart, TEMPLATE, clock=lambda: NOW)

    assert voice.compose() == "(Por dentro:\n- Você está muito curiosa.)"


def test_tells_her_heart_how_many_wishes_are_still_waiting(heart: FixedHeart) -> None:
    archive = InMemorySuggestionArchive(
        [a_suggestion("Vaga-lumes"), a_suggestion("Um laguinho"), a_suggestion("Uma luneta")]
    )
    archive.suggestions[0] = replace(archive.suggestions[0]).built()
    voice = FeelingsVoice(heart, TEMPLATE, archive, clock=lambda: NOW)

    voice.compose()

    assert heart.told_pending_wishes == [2]


def test_without_suggestions_the_wishes_are_left_as_they_were(heart: FixedHeart) -> None:
    FeelingsVoice(heart, TEMPLATE, clock=lambda: NOW).compose()

    assert heart.told_pending_wishes == [None]
