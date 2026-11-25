from datetime import date, datetime

import pytest

from src.application.diary_mood_words import day_mood_word, entry_mood_word
from src.domain.diary import DiaryDay, DiaryEntry, DiaryMood
from src.domain.feelings.emotion import Emotion

WRITTEN_AT = datetime(2026, 11, 25, 14, 30)


def day_with_valences(*valences: float) -> DiaryDay:
    entries = tuple(
        DiaryEntry(WRITTEN_AT, "Um pensamento.", DiaryMood(None, valence)) for valence in valences
    )
    return DiaryDay(date(2026, 11, 25), entries)


def test_an_entry_mood_uses_the_word_of_her_strongest_emotion() -> None:
    assert entry_mood_word(DiaryMood(Emotion.LONELINESS, -0.3)) == "sozinha"


def test_an_entry_without_a_strong_emotion_is_calm() -> None:
    assert entry_mood_word(DiaryMood(None, 0.05)) == "tranquila"


@pytest.mark.parametrize(
    ("valences", "expected_word"),
    [
        ((0.6, 0.4), "um dia muito bom"),
        ((0.2,), "um dia bom"),
        ((0.3, -0.3), "um dia tranquilo"),
        ((-0.2,), "um dia difícil"),
        ((-0.5, -0.7), "um dia muito difícil"),
    ],
)
def test_the_day_word_follows_the_average_of_her_moods(
    valences: tuple[float, ...], expected_word: str
) -> None:
    assert day_mood_word(day_with_valences(*valences)) == expected_word


def test_a_day_without_moods_has_no_word() -> None:
    day = DiaryDay(date(2026, 11, 25), (DiaryEntry(WRITTEN_AT, "Sem humor."),))

    assert day_mood_word(day) is None
