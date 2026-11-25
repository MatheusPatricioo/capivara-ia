from datetime import datetime

import pytest

from src.domain.letter import MAX_LETTER_LENGTH, Letter, LetterStatus, Reply, SavedLetter
from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_messages import (
    LetterMessage,
    LetterOpenedMessage,
    LetterRepliedMessage,
    NoticedMessage,
    mailbox_message,
    parse_world_event,
)

OLD_LETTER = SavedLetter(
    "carta-1.md", Letter(datetime(2026, 11, 24, 9, 5), "Bom dia!", LetterStatus.READ)
)
NEW_LETTER = SavedLetter("carta-2.md", Letter(datetime(2026, 11, 25, 14, 30), "Oi, criador!"))


class RecordingHandlers:
    def __init__(self) -> None:
        self.noticed: list[NoticedMessage] = []
        self.opened: list[str] = []
        self.replied: list[tuple[str, str]] = []


@pytest.fixture
def handlers() -> RecordingHandlers:
    return RecordingHandlers()


@pytest.fixture
def router(handlers: RecordingHandlers) -> WorldEventRouter:
    return WorldEventRouter(on_noticed=handlers.noticed.append)


def test_mailbox_message_lists_the_newest_letter_first() -> None:
    message = mailbox_message([OLD_LETTER, NEW_LETTER])

    assert [letter.file_name for letter in message.letters] == ["carta-2.md", "carta-1.md"]


def test_mailbox_message_carries_each_letter_with_its_date_and_status() -> None:
    assert mailbox_message([NEW_LETTER]).letters == [
        LetterMessage(
            file_name="carta-2.md",
            written_at="2026-11-25T14:30",
            text="Oi, criador!",
            unread=True,
        )
    ]


def test_parses_a_letter_opened_event() -> None:
    event = parse_world_event('{"type": "letter_opened", "letter": "carta-2.md"}')

    assert event == LetterOpenedMessage(letter="carta-2.md")


def test_ignores_a_letter_opened_event_without_a_letter() -> None:
    assert parse_world_event('{"type": "letter_opened", "letter": ""}') is None


def test_routes_a_noticed_event_to_the_attention(
    router: WorldEventRouter, handlers: RecordingHandlers
) -> None:
    noticed = NoticedMessage(thing="pond", description="o laguinho")

    router.route(noticed)

    assert handlers.noticed == [noticed]


def test_routes_a_letter_opened_event_to_the_mailbox(
    router: WorldEventRouter, handlers: RecordingHandlers
) -> None:
    router.when_letter_opened(handlers.opened.append)

    router.route(LetterOpenedMessage(letter="carta-2.md"))

    assert handlers.opened == ["carta-2.md"]


def test_a_letter_opened_without_a_mailbox_reaches_no_one(
    router: WorldEventRouter, handlers: RecordingHandlers
) -> None:
    router.route(LetterOpenedMessage(letter="carta-2.md"))

    assert handlers.opened == []


ANSWERED_LETTER = SavedLetter(
    "carta-3.md", NEW_LETTER.letter.answered(Reply(datetime(2026, 11, 26, 10, 0), "Volto amanhã."))
)


def test_mailbox_message_carries_the_reply_with_its_date() -> None:
    letter = mailbox_message([ANSWERED_LETTER]).letters[0]

    assert (letter.replied_at, letter.reply) == ("2026-11-26T10:00", "Volto amanhã.")


def test_mailbox_message_has_no_reply_for_an_unanswered_letter() -> None:
    letter = mailbox_message([NEW_LETTER]).letters[0]

    assert (letter.replied_at, letter.reply) == (None, None)


def test_parses_a_letter_replied_event() -> None:
    event = parse_world_event(
        '{"type": "letter_replied", "letter": "carta-2.md", "text": " Volto amanhã. "}'
    )

    assert event == LetterRepliedMessage(letter="carta-2.md", text="Volto amanhã.")


def test_ignores_an_empty_reply() -> None:
    event = parse_world_event('{"type": "letter_replied", "letter": "carta-2.md", "text": " "}')

    assert event is None


def test_ignores_a_reply_longer_than_a_letter() -> None:
    long_text = "a" * (MAX_LETTER_LENGTH + 1)

    event = parse_world_event(
        f'{{"type": "letter_replied", "letter": "carta-2.md", "text": "{long_text}"}}'
    )

    assert event is None


def test_routes_a_reply_to_the_mailbox(
    router: WorldEventRouter, handlers: RecordingHandlers
) -> None:
    router.when_letter_replied(lambda file_name, text: handlers.replied.append((file_name, text)))

    router.route(LetterRepliedMessage(letter="carta-2.md", text="Volto amanhã."))

    assert handlers.replied == [("carta-2.md", "Volto amanhã.")]


def test_a_reply_without_a_mailbox_reaches_no_one(
    router: WorldEventRouter, handlers: RecordingHandlers
) -> None:
    router.route(LetterRepliedMessage(letter="carta-2.md", text="Volto amanhã."))

    assert handlers.replied == []
