from datetime import date, datetime

import pytest

from src.application.diary_keeper import DiaryKeeper
from src.domain.diary import DiaryDay, DiaryEntry, DiaryMood
from src.domain.feelings.emotion import Emotion, EmotionalState
from tests.fakes.in_memory_diary import BrokenDiary, InMemoryDiary

NOW = datetime(2026, 11, 25, 14, 30)


@pytest.fixture
def diary() -> InMemoryDiary:
    return InMemoryDiary()


@pytest.fixture
def keeper(diary: InMemoryDiary) -> DiaryKeeper:
    return DiaryKeeper(diary, now=lambda: NOW)


def test_keeps_her_thought_with_the_time_she_had_it(
    keeper: DiaryKeeper, diary: InMemoryDiary
) -> None:
    keeper.keep("Hoje pesquisei sobre vaga-lumes.")

    assert diary.recent_days(limit=1) == [
        DiaryDay(date(2026, 11, 25), (DiaryEntry(NOW, "Hoje pesquisei sobre vaga-lumes."),))
    ]


def test_an_empty_thought_is_not_kept(keeper: DiaryKeeper, diary: InMemoryDiary) -> None:
    keeper.keep("   ")

    assert diary.recent_days(limit=1) == []


def test_without_feelings_the_entry_has_no_mood(keeper: DiaryKeeper, diary: InMemoryDiary) -> None:
    keeper.keep("Hoje pesquisei sobre vaga-lumes.")

    assert diary.recent_days(limit=1)[0].entries[0].mood is None


def test_with_feelings_the_entry_records_her_mood(diary: InMemoryDiary) -> None:
    happy = EmotionalState({Emotion.JOY: 0.8})
    keeper = DiaryKeeper(diary, feelings=lambda: happy, now=lambda: NOW)

    keeper.keep("Hoje pesquisei sobre vaga-lumes.")

    assert diary.recent_days(limit=1)[0].entries[0].mood == DiaryMood.of(happy)


def test_a_broken_diary_does_not_stop_her() -> None:
    keeper = DiaryKeeper(BrokenDiary(), now=lambda: NOW)

    keeper.keep("Hoje pesquisei sobre vaga-lumes.")
