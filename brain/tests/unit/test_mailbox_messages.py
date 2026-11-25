from datetime import datetime

import pytest

from src.domain.letter import Letter, LetterStatus, SavedLetter
from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_messages import (
    LetterMessage,
    LetterOpenedMessage,
    NoticedMessage,
    mailbox_message,
    parse_world_event,
)

OLD_LETTER = SavedLetter(
    "carta-1.md", Letter(datetime(2026, 11, 24, 9, 5), "Bom dia!", LetterStatus.READ)
)
NEW_LETTER = SavedLetter("carta-2.md", Letter(datetime(2026, 11, 25, 14, 30), "Oi, Matheus!"))


class RecordingHandlers:
    def __init__(self) -> None:
        self.noticed: list[NoticedMessage] = []
        self.opened: list[str] = []


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
            text="Oi, Matheus!",
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
