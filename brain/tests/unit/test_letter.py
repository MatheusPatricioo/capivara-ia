from datetime import datetime, timedelta

import pytest

from src.domain.letter import (
    MAX_LETTER_LENGTH,
    InvalidLetterError,
    Letter,
    LetterRhythm,
    LetterStatus,
)

NOW = datetime(2026, 11, 25, 14, 0)


def letter_written(hours_ago: float, status: LetterStatus = LetterStatus.READ) -> Letter:
    return Letter(NOW - timedelta(hours=hours_ago), "Oi, Matheus!", status)


@pytest.fixture
def rhythm() -> LetterRhythm:
    return LetterRhythm(min_hours_between=20.0, max_unread=2)


def test_a_new_letter_is_unread() -> None:
    assert Letter(NOW, "Oi, Matheus!").is_unread


def test_trims_spaces_around_the_text() -> None:
    assert Letter(NOW, "  Oi, Matheus!\n").text == "Oi, Matheus!"


def test_rejects_an_empty_letter() -> None:
    with pytest.raises(InvalidLetterError):
        Letter(NOW, "   ")


def test_rejects_a_letter_longer_than_the_limit() -> None:
    with pytest.raises(InvalidLetterError):
        Letter(NOW, "a" * (MAX_LETTER_LENGTH + 1))


def test_the_first_letter_is_always_allowed(rhythm: LetterRhythm) -> None:
    assert rhythm.allows_a_new_letter([], NOW)


def test_waits_the_minimum_hours_after_her_last_letter(rhythm: LetterRhythm) -> None:
    assert not rhythm.allows_a_new_letter([letter_written(hours_ago=19)], NOW)


def test_writes_again_after_the_minimum_hours(rhythm: LetterRhythm) -> None:
    assert rhythm.allows_a_new_letter([letter_written(hours_ago=20)], NOW)


def test_stops_writing_while_too_many_letters_wait_unread(rhythm: LetterRhythm) -> None:
    letters = [
        letter_written(hours_ago=60, status=LetterStatus.UNREAD),
        letter_written(hours_ago=30, status=LetterStatus.UNREAD),
    ]

    assert not rhythm.allows_a_new_letter(letters, NOW)


def test_rejects_a_rhythm_without_room_for_unread_letters() -> None:
    with pytest.raises(ValueError):
        LetterRhythm(max_unread=0)


def test_an_opened_letter_is_read() -> None:
    assert not Letter(NOW, "Oi, Matheus!").opened().is_unread


def test_opening_keeps_the_text() -> None:
    assert Letter(NOW, "Oi, Matheus!").opened().text == "Oi, Matheus!"
