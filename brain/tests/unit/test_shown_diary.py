from datetime import date, datetime

import pytest

from src.application.shown_diary import ShownDiary
from src.domain.diary import DiaryDay, DiaryEntry
from tests.fakes.in_memory_diary import BrokenDiary, InMemoryDiary

YESTERDAY = DiaryEntry(datetime(2026, 11, 24, 20, 0), "Choveu o dia todo.")
TODAY = DiaryEntry(datetime(2026, 11, 25, 14, 30), "Hoje pesquisei sobre vaga-lumes.")


class RecordingDisplay:
    def __init__(self) -> None:
        self.shown: list[list[DiaryDay]] = []

    def show_diary(self, days: list[DiaryDay]) -> None:
        self.shown.append(days)


@pytest.fixture
def display() -> RecordingDisplay:
    return RecordingDisplay()


@pytest.fixture
def diary(display: RecordingDisplay) -> ShownDiary:
    return ShownDiary(InMemoryDiary(), display)


def test_shows_the_diary_after_a_new_entry(diary: ShownDiary, display: RecordingDisplay) -> None:
    diary.write(TODAY)

    assert display.shown == [[DiaryDay(date(2026, 11, 25), (TODAY,))]]


def test_keeps_the_entry_in_the_diary_it_wraps(diary: ShownDiary) -> None:
    diary.write(TODAY)

    assert diary.recent_days(limit=1) == [DiaryDay(date(2026, 11, 25), (TODAY,))]


def test_shows_only_the_latest_days(display: RecordingDisplay) -> None:
    diary = ShownDiary(InMemoryDiary(), display, shown_days=1)
    diary.write(YESTERDAY)

    diary.write(TODAY)

    assert display.shown[-1] == [DiaryDay(date(2026, 11, 25), (TODAY,))]


def test_shows_an_empty_diary_when_asked(diary: ShownDiary, display: RecordingDisplay) -> None:
    diary.show()

    assert display.shown == [[]]


def test_a_broken_diary_shows_nothing(display: RecordingDisplay) -> None:
    ShownDiary(BrokenDiary(), display).show()

    assert display.shown == []
