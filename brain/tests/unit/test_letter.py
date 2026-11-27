from datetime import datetime, timedelta

import pytest

from src.domain.letter import (
    MAX_LETTER_LENGTH,
    InvalidLetterError,
    Letter,
    LetterRhythm,
    LetterStatus,
    Reply,
)

NOW = datetime(2026, 11, 25, 14, 0)


def letter_written(hours_ago: float, status: LetterStatus = LetterStatus.READ) -> Letter:
    return Letter(NOW - timedelta(hours=hours_ago), "Oi, criador!", status)


@pytest.fixture
def rhythm() -> LetterRhythm:
    return LetterRhythm(min_hours_between=20.0, max_unread=2)


def test_a_new_letter_is_unread() -> None:
    assert Letter(NOW, "Oi, criador!").is_unread


def test_trims_spaces_around_the_text() -> None:
    assert Letter(NOW, "  Oi, criador!\n").text == "Oi, criador!"


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
    assert not Letter(NOW, "Oi, criador!").opened().is_unread


def test_opening_keeps_the_text() -> None:
    assert Letter(NOW, "Oi, criador!").opened().text == "Oi, criador!"


def test_an_answered_letter_keeps_the_reply() -> None:
    reply = Reply(NOW, "Oi, capivara! Volto amanhã.")

    assert Letter(NOW, "Oi, criador!").answered(reply).reply == reply


def test_an_answered_letter_is_read() -> None:
    letter = Letter(NOW, "Oi, criador!").answered(Reply(NOW, "Oi!"))

    assert not letter.is_unread


def test_a_letter_gets_only_one_reply() -> None:
    letter = Letter(NOW, "Oi, criador!").answered(Reply(NOW, "Oi!"))

    with pytest.raises(InvalidLetterError):
        letter.answered(Reply(NOW, "Oi de novo!"))


def test_rejects_an_empty_reply() -> None:
    with pytest.raises(InvalidLetterError):
        Reply(NOW, "  ")


def test_a_fresh_reply_is_new_to_her() -> None:
    letter = Letter(NOW, "Oi, criador!").answered(Reply(NOW, "Oi!"))

    assert letter.has_a_new_reply


def test_a_reply_she_read_is_no_longer_new() -> None:
    letter = Letter(NOW, "Oi, criador!").answered(Reply(NOW, "Oi!")).reply_seen()

    assert not letter.has_a_new_reply


def test_an_unanswered_letter_has_no_new_reply() -> None:
    assert not Letter(NOW, "Oi, criador!").has_a_new_reply


def test_cannot_read_the_reply_of_an_unanswered_letter() -> None:
    with pytest.raises(InvalidLetterError):
        Letter(NOW, "Oi, criador!").reply_seen()
