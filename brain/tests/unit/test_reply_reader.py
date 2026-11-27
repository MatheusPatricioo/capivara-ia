from datetime import datetime

import pytest

from src.application.reply_reader import ReplyReader
from src.domain.body import Place
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.letter import Letter, Reply
from tests.fakes.in_memory_mailbox import BrokenMailbox, InMemoryMailbox

TEMPLATE = "Ele respondeu!\n{replies}"
WRITTEN_AT = datetime(2026, 11, 25, 14, 30)
UNANSWERED = Letter(WRITTEN_AT, "Oi, criador! Achei uma estrela nova.")
ANSWERED = UNANSWERED.answered(Reply(datetime(2026, 11, 26, 10, 0), "Que legal! Me conta mais."))
LETTER_ANSWERED = EmotionalEvent(EventKind.LETTER_ANSWERED)


class RecordingHeart:
    def __init__(self) -> None:
        self.felt: list[EmotionalEvent] = []

    def feel(self, event: EmotionalEvent) -> EmotionalLife:
        self.felt.append(event)
        return EmotionalLife(EmotionalLife.newborn(0.0))


class RecordingBody:
    def __init__(self) -> None:
        self.visited_places: list[Place] = []

    def go_to(self, place: Place) -> None:
        self.visited_places.append(place)


@pytest.fixture
def heart() -> RecordingHeart:
    return RecordingHeart()


@pytest.fixture
def body() -> RecordingBody:
    return RecordingBody()


@pytest.fixture
def mailbox() -> InMemoryMailbox:
    return InMemoryMailbox([UNANSWERED, ANSWERED])


@pytest.fixture
def reader(mailbox: InMemoryMailbox, heart: RecordingHeart, body: RecordingBody) -> ReplyReader:
    return ReplyReader(mailbox, heart, TEMPLATE, body=body)


def test_a_new_reply_moves_her(reader: ReplyReader, heart: RecordingHeart) -> None:
    reader.read_new_replies()

    assert heart.felt == [LETTER_ANSWERED]


def test_she_walks_to_the_mailbox_to_read_it(reader: ReplyReader, body: RecordingBody) -> None:
    reader.read_new_replies()

    assert body.visited_places == [Place.MAILBOX]


def test_her_inner_voice_tells_her_letter_and_his_reply(reader: ReplyReader) -> None:
    reader.read_new_replies()

    assert reader.compose() == (
        "Ele respondeu!\n"
        'Sua cartinha de 25/11: "Oi, criador! Achei uma estrela nova."\n'
        'A resposta dele: "Que legal! Me conta mais."'
    )


def test_a_long_letter_is_only_remembered_in_part(heart: RecordingHeart) -> None:
    long_letter = Letter(WRITTEN_AT, "a" * 300).answered(Reply(WRITTEN_AT, "Oi!"))
    reader = ReplyReader(InMemoryMailbox([long_letter]), heart, TEMPLATE)
    reader.read_new_replies()

    assert '"' + "a" * 200 + '..."' in reader.compose()


def test_without_replies_she_stays_where_she_is(heart: RecordingHeart, body: RecordingBody) -> None:
    reader = ReplyReader(InMemoryMailbox([UNANSWERED]), heart, TEMPLATE, body=body)

    reader.read_new_replies()

    assert (body.visited_places, heart.felt, reader.compose()) == ([], [], "")


def test_after_the_cycle_the_reply_is_remembered_as_read(
    reader: ReplyReader, mailbox: InMemoryMailbox
) -> None:
    reader.read_new_replies()

    reader.release()

    assert not mailbox.posted[1].has_a_new_reply


def test_a_read_reply_does_not_come_back(reader: ReplyReader, heart: RecordingHeart) -> None:
    reader.read_new_replies()
    reader.release()

    reader.read_new_replies()

    assert (heart.felt, reader.compose()) == ([LETTER_ANSWERED], "")


def test_after_a_failed_cycle_the_reply_is_offered_again(reader: ReplyReader) -> None:
    reader.read_new_replies()

    reader.read_new_replies()

    assert "Que legal! Me conta mais." in reader.compose()


def test_a_reply_offered_again_moves_her_only_once(
    reader: ReplyReader, heart: RecordingHeart
) -> None:
    reader.read_new_replies()

    reader.read_new_replies()

    assert heart.felt == [LETTER_ANSWERED]


def test_a_broken_mailbox_offers_nothing(heart: RecordingHeart) -> None:
    reader = ReplyReader(BrokenMailbox(), heart, TEMPLATE)

    reader.read_new_replies()

    assert reader.compose() == ""
