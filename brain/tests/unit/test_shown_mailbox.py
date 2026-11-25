from datetime import datetime

import pytest

from src.application.shown_mailbox import ShownMailbox
from src.domain.letter import Letter, SavedLetter
from tests.fakes.in_memory_mailbox import InMemoryMailbox

LETTER = Letter(datetime(2026, 11, 25, 14, 30), "Oi, Matheus!")


class RecordingDisplay:
    def __init__(self) -> None:
        self.shown: list[list[SavedLetter]] = []

    def show_mailbox(self, letters: list[SavedLetter]) -> None:
        self.shown.append(letters)


@pytest.fixture
def display() -> RecordingDisplay:
    return RecordingDisplay()


@pytest.fixture
def mailbox(display: RecordingDisplay) -> ShownMailbox:
    return ShownMailbox(InMemoryMailbox(), display)


def test_shows_the_new_letter_when_it_is_posted(
    mailbox: ShownMailbox, display: RecordingDisplay
) -> None:
    file_name = mailbox.post(LETTER)

    assert display.shown == [[SavedLetter(file_name, LETTER)]]


def test_shows_the_letter_as_read_when_matheus_opens_it(
    mailbox: ShownMailbox, display: RecordingDisplay
) -> None:
    file_name = mailbox.post(LETTER)

    mailbox.open_letter(file_name)

    assert display.shown[-1] == [SavedLetter(file_name, LETTER.opened())]


def test_opening_an_unknown_letter_shows_nothing_new(
    mailbox: ShownMailbox, display: RecordingDisplay
) -> None:
    mailbox.open_letter("carta-que-nao-existe.md")

    assert display.shown == []


def test_show_sends_the_letters_already_in_the_mailbox(display: RecordingDisplay) -> None:
    mailbox = ShownMailbox(InMemoryMailbox([LETTER]), display)

    mailbox.show()

    assert display.shown == [[SavedLetter("carta-1.md", LETTER)]]
