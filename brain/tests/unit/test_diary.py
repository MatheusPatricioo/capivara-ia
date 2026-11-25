from datetime import datetime

import pytest

from src.domain.diary import MAX_DIARY_ENTRY_LENGTH, DiaryEntry, InvalidDiaryEntryError

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
