from collections.abc import Sequence
from datetime import datetime, timedelta

import pytest

from src.application.letter_writer import FIRST_LETTER, LetterWriter
from src.domain.body import Place
from src.domain.discovery import DiscoveryHeadline
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.feelings.needs import Need
from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    ToolDefinition,
)
from src.domain.letter import Letter, LetterRhythm, LetterStatus
from tests.fakes.emotional_lives import NOW, a_life
from tests.fakes.in_memory_mailbox import BrokenMailbox, InMemoryMailbox

WRITTEN_AT = datetime(2026, 11, 25, 14, 0)
LETTER_TEXT = "Oi, Matheus! Senti sua falta hoje no laguinho. Volta logo? Capivara"
LETTER_PROMPT = "Carta.\n{feelings}\n{mailbox}\n{discoveries}"
CONNECTED_RUNG = 0
MISSING_HIM_RUNG = 1


class FixedHeart:
    def __init__(self, life: EmotionalLife) -> None:
        self._life = life

    def check_in(self, pending_wishes: int | None = None) -> EmotionalLife:
        return self._life


class WritingLanguageModel:
    """Always writes the same letter and records what it was asked."""

    def __init__(self) -> None:
        self.received: list[list[ChatMessage]] = []

    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        self.received.append(messages)
        return ChatMessage(Role.ASSISTANT, LETTER_TEXT)


class OfflineLanguageModel:
    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        raise LanguageModelError("Ollama is not running")


class OneDiscoveryCatalog:
    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        return [DiscoveryHeadline(title="Vaga-lumes", topic="insetos")]


@pytest.fixture
def mailbox() -> InMemoryMailbox:
    return InMemoryMailbox()


@pytest.fixture
def language_model() -> WritingLanguageModel:
    return WritingLanguageModel()


class RecordingBody:
    def __init__(self) -> None:
        self.visited_places: list[Place] = []

    def go_to(self, place: Place) -> None:
        self.visited_places.append(place)


def writer_for(
    bond_rung: int,
    mailbox: InMemoryMailbox | BrokenMailbox,
    language_model: WritingLanguageModel | OfflineLanguageModel,
    body: RecordingBody | None = None,
) -> LetterWriter:
    return LetterWriter(
        FixedHeart(a_life(rungs={Need.BOND: bond_rung}, hours_since_talked=30)),
        mailbox,
        OneDiscoveryCatalog(),
        language_model,
        system_prompt="Você é uma capivara.",
        letter_prompt=LETTER_PROMPT,
        rhythm=LetterRhythm(min_hours_between=20.0, max_unread=3),
        now=lambda: WRITTEN_AT,
        clock=lambda: NOW,
        body=body,
    )


def test_writes_nothing_while_she_does_not_miss_him(
    mailbox: InMemoryMailbox, language_model: WritingLanguageModel
) -> None:
    writer_for(CONNECTED_RUNG, mailbox, language_model).maybe_write()

    assert mailbox.posted == []


def test_posts_a_letter_when_she_misses_him(
    mailbox: InMemoryMailbox, language_model: WritingLanguageModel
) -> None:
    writer_for(MISSING_HIM_RUNG, mailbox, language_model).maybe_write()

    assert mailbox.posted == [Letter(WRITTEN_AT, LETTER_TEXT)]


def test_returns_the_file_name_of_the_new_letter(
    mailbox: InMemoryMailbox, language_model: WritingLanguageModel
) -> None:
    assert writer_for(MISSING_HIM_RUNG, mailbox, language_model).maybe_write() == "carta-1.md"


def test_walks_to_the_mailbox_to_leave_the_letter(
    mailbox: InMemoryMailbox, language_model: WritingLanguageModel
) -> None:
    body = RecordingBody()

    writer_for(MISSING_HIM_RUNG, mailbox, language_model, body).maybe_write()

    assert body.visited_places == [Place.MAILBOX]


def test_writes_in_her_voice_from_the_system_prompt(
    mailbox: InMemoryMailbox, language_model: WritingLanguageModel
) -> None:
    writer_for(MISSING_HIM_RUNG, mailbox, language_model).maybe_write()

    assert language_model.received[0][0] == ChatMessage(Role.SYSTEM, "Você é uma capivara.")


def test_tells_her_it_is_her_first_letter(
    mailbox: InMemoryMailbox, language_model: WritingLanguageModel
) -> None:
    writer_for(MISSING_HIM_RUNG, mailbox, language_model).maybe_write()

    assert FIRST_LETTER in language_model.received[0][1].content


def test_tells_her_the_last_unread_letter_so_she_does_not_repeat_it(
    language_model: WritingLanguageModel,
) -> None:
    old_letter = Letter(
        WRITTEN_AT - timedelta(hours=30), "Oi! Hoje vi um sapo.", LetterStatus.UNREAD
    )

    writer_for(MISSING_HIM_RUNG, InMemoryMailbox([old_letter]), language_model).maybe_write()

    assert '"Oi! Hoje vi um sapo."' in language_model.received[0][1].content


def test_tells_her_latest_discoveries(
    mailbox: InMemoryMailbox, language_model: WritingLanguageModel
) -> None:
    writer_for(MISSING_HIM_RUNG, mailbox, language_model).maybe_write()

    assert "- Vaga-lumes (insetos)" in language_model.received[0][1].content


def test_does_not_write_again_too_soon(language_model: WritingLanguageModel) -> None:
    recent_letter = Letter(WRITTEN_AT - timedelta(hours=2), "Oi!", LetterStatus.READ)
    mailbox = InMemoryMailbox([recent_letter])

    writer_for(MISSING_HIM_RUNG, mailbox, language_model).maybe_write()

    assert language_model.received == []


def test_writes_nothing_when_the_model_is_offline(mailbox: InMemoryMailbox) -> None:
    writer_for(MISSING_HIM_RUNG, mailbox, OfflineLanguageModel()).maybe_write()

    assert mailbox.posted == []


def test_returns_none_when_the_mailbox_cannot_be_written(
    language_model: WritingLanguageModel,
) -> None:
    assert writer_for(MISSING_HIM_RUNG, BrokenMailbox(), language_model).maybe_write() is None
