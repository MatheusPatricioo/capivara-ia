from datetime import date, datetime

import pytest

from src.domain.diary import (
    MAX_DIARY_ENTRY_LENGTH,
    DiaryDay,
    DiaryEntry,
    DiaryMood,
    InvalidDiaryEntryError,
)
from src.domain.feelings.emotion import Emotion, EmotionalState

WRITTEN_AT = datetime(2026, 11, 25, 14, 30)


def test_an_entry_keeps_the_text_without_spaces_around_it() -> None:
    assert DiaryEntry(WRITTEN_AT, "  Hoje vi vaga-lumes.\n").text == "Hoje vi vaga-lumes."


def test_an_empty_entry_is_refused() -> None:
    with pytest.raises(InvalidDiaryEntryError):
        DiaryEntry(WRITTEN_AT, "   ")


def test_a_too_long_entry_is_refused() -> None:
    with pytest.raises(InvalidDiaryEntryError):
        DiaryEntry(WRITTEN_AT, "a" * (MAX_DIARY_ENTRY_LENGTH + 1))


def test_an_entry_of_the_maximum_length_is_accepted() -> None:
    text = "a" * MAX_DIARY_ENTRY_LENGTH

    assert DiaryEntry(WRITTEN_AT, text).text == text


def test_a_mood_records_her_strongest_emotion_and_how_good_she_felt() -> None:
    emotions = EmotionalState({Emotion.JOY: 0.8, Emotion.CURIOSITY: 0.3})

    assert DiaryMood.of(emotions) == DiaryMood(Emotion.JOY, 0.52)


def test_a_mood_without_a_strong_emotion_is_calm() -> None:
    emotions = EmotionalState({Emotion.CURIOSITY: 0.1})

    assert DiaryMood.of(emotions).emotion is None


def test_a_mood_valence_out_of_range_is_refused() -> None:
    with pytest.raises(InvalidDiaryEntryError):
        DiaryMood(Emotion.JOY, 1.5)


def test_a_day_averages_the_moods_of_its_entries() -> None:
    day = DiaryDay(
        date(2026, 11, 25),
        (
            DiaryEntry(WRITTEN_AT, "Bom.", DiaryMood(Emotion.JOY, 0.6)),
            DiaryEntry(WRITTEN_AT, "Ruim.", DiaryMood(Emotion.SADNESS, -0.2)),
            DiaryEntry(WRITTEN_AT, "Sem humor."),
        ),
    )

    assert day.average_valence == pytest.approx(0.2)


def test_a_day_without_moods_has_no_average() -> None:
    day = DiaryDay(date(2026, 11, 25), (DiaryEntry(WRITTEN_AT, "Sem humor."),))

    assert day.average_valence is None
