import logging
from collections.abc import Sequence

import pytest

from src.application.conversation import Conversation
from src.application.creator_chat import CreatorChat
from src.application.creator_presence import CreatorPresence
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.language_model import ChatMessage, LanguageModelError, Role, ToolDefinition
from tests.fakes.in_memory_emotional_memory import RecordingFeeler
from tests.fakes.manual_time import ManualTime

QUIET_SECONDS = 120.0
MESSAGE = "Oi, capivara! O que você está fazendo?"
REPLY = "Oi, criador! Estava lendo sobre vaga-lumes."


class ReplyingLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        return ChatMessage(Role.ASSISTANT, REPLY)


class OfflineLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        raise LanguageModelError("Ollama is offline")


class RecordingDisplay:
    def __init__(self) -> None:
        self.listening_seconds: list[float] = []
        self.replies: list[str] = []

    def show_listening(self, seconds: float) -> None:
        self.listening_seconds.append(seconds)

    def show_reply(self, reply: str) -> None:
        self.replies.append(reply)


@pytest.fixture
def time() -> ManualTime:
    return ManualTime()


@pytest.fixture
def presence(time: ManualTime) -> CreatorPresence:
    return CreatorPresence(QUIET_SECONDS, clock=time.clock, sleep=time.sleep)


@pytest.fixture
def display() -> RecordingDisplay:
    return RecordingDisplay()


@pytest.fixture
def heart() -> RecordingFeeler:
    return RecordingFeeler()


@pytest.fixture
def chat(
    presence: CreatorPresence, display: RecordingDisplay, heart: RecordingFeeler
) -> CreatorChat:
    conversation = Conversation(ReplyingLanguageModel(), "Você é uma capivara.")
    return CreatorChat(conversation, presence, display, heart)


@pytest.fixture
def offline_chat(presence: CreatorPresence, display: RecordingDisplay) -> CreatorChat:
    conversation = Conversation(OfflineLanguageModel(), "Você é uma capivara.")
    return CreatorChat(conversation, presence, display)


def test_hearing_a_message_starts_the_conversation(
    chat: CreatorChat, presence: CreatorPresence
) -> None:
    chat.hear()

    assert presence.is_talking()


def test_hearing_a_message_makes_her_listen_for_the_quiet_time(
    chat: CreatorChat, display: RecordingDisplay
) -> None:
    chat.hear()

    assert display.listening_seconds == [QUIET_SECONDS]


def test_her_reply_is_shown(chat: CreatorChat, display: RecordingDisplay) -> None:
    chat.answer(MESSAGE)

    assert display.replies == [REPLY]


def test_her_reply_renews_the_quiet_time(
    chat: CreatorChat, presence: CreatorPresence, time: ManualTime
) -> None:
    chat.hear()
    time.now += 100.0

    chat.answer(MESSAGE)
    time.now += 100.0

    assert presence.is_talking()


def test_talking_with_her_creator_is_felt_by_her_heart(
    chat: CreatorChat, heart: RecordingFeeler
) -> None:
    chat.answer(MESSAGE)

    assert heart.felt == [EmotionalEvent(EventKind.TALKED_WITH_MATHEUS)]


def test_a_failed_answer_shows_no_reply(
    offline_chat: CreatorChat, display: RecordingDisplay
) -> None:
    offline_chat.answer(MESSAGE)

    assert display.replies == []


def test_a_failed_answer_is_logged(
    offline_chat: CreatorChat, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        offline_chat.answer(MESSAGE)

    assert "could not answer her creator" in caplog.text
