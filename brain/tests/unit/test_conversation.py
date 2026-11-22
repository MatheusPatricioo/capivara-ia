from collections.abc import Sequence

import pytest

from src.application.conversation import Conversation
from src.domain.language_model import ChatMessage, LanguageModelError, Role, ToolDefinition

SYSTEM_PROMPT = "You are a curious capybara."
FIRST_QUESTION = "What do you want to research today?"
FIRST_REPLY = "The stars."
SECOND_QUESTION = "Why the stars?"
SECOND_REPLY = "Because they shine at night."


class RecordingLanguageModel:
    def __init__(self, replies: list[str]) -> None:
        self._replies = iter(replies)
        self.received_histories: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.received_histories.append(messages)
        return ChatMessage(Role.ASSISTANT, next(self._replies))


class OfflineLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        raise LanguageModelError("model is offline")


@pytest.fixture
def recording_language_model() -> RecordingLanguageModel:
    return RecordingLanguageModel(replies=[FIRST_REPLY, SECOND_REPLY])


@pytest.fixture
def conversation(recording_language_model: RecordingLanguageModel) -> Conversation:
    return Conversation(recording_language_model, SYSTEM_PROMPT)


@pytest.fixture
def offline_conversation() -> Conversation:
    return Conversation(OfflineLanguageModel(), SYSTEM_PROMPT)


def test_returns_the_model_reply(conversation: Conversation) -> None:
    reply = conversation.send(FIRST_QUESTION)

    assert reply == FIRST_REPLY


def test_first_turn_sends_system_prompt_and_user_message(
    conversation: Conversation, recording_language_model: RecordingLanguageModel
) -> None:
    conversation.send(FIRST_QUESTION)

    assert recording_language_model.received_histories[0] == [
        ChatMessage(Role.SYSTEM, SYSTEM_PROMPT),
        ChatMessage(Role.USER, FIRST_QUESTION),
    ]


def test_second_turn_resends_the_whole_history(
    conversation: Conversation, recording_language_model: RecordingLanguageModel
) -> None:
    conversation.send(FIRST_QUESTION)
    conversation.send(SECOND_QUESTION)

    assert recording_language_model.received_histories[1] == [
        ChatMessage(Role.SYSTEM, SYSTEM_PROMPT),
        ChatMessage(Role.USER, FIRST_QUESTION),
        ChatMessage(Role.ASSISTANT, FIRST_REPLY),
        ChatMessage(Role.USER, SECOND_QUESTION),
    ]


def test_history_grows_by_two_messages_per_turn(conversation: Conversation) -> None:
    conversation.send(FIRST_QUESTION)
    conversation.send(SECOND_QUESTION)

    assert len(conversation.history) == 5


def test_propagates_the_error_when_the_model_is_offline(
    offline_conversation: Conversation,
) -> None:
    with pytest.raises(LanguageModelError):
        offline_conversation.send(FIRST_QUESTION)


def test_keeps_history_unchanged_when_the_model_fails(
    offline_conversation: Conversation,
) -> None:
    with pytest.raises(LanguageModelError):
        offline_conversation.send(FIRST_QUESTION)

    assert offline_conversation.history == (ChatMessage(Role.SYSTEM, SYSTEM_PROMPT),)
