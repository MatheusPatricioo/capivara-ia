from collections.abc import Sequence

import pytest

from src.application.ask_question import AskQuestion
from src.domain.language_model import ChatMessage, LanguageModelError, Role, ToolDefinition

SYSTEM_PROMPT = "You are a curious crow."
QUESTION = "What do you want to research today?"
MODEL_REPLY = "I want to research the stars."


class FakeLanguageModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.received_messages: list[ChatMessage] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.received_messages = messages
        return ChatMessage(Role.ASSISTANT, self.reply)


class OfflineLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        raise LanguageModelError("model is offline")


@pytest.fixture
def fake_language_model() -> FakeLanguageModel:
    return FakeLanguageModel(reply=MODEL_REPLY)


@pytest.fixture
def ask_question(fake_language_model: FakeLanguageModel) -> AskQuestion:
    return AskQuestion(fake_language_model)


def test_returns_the_model_reply(ask_question: AskQuestion) -> None:
    reply = ask_question.execute(system_prompt=SYSTEM_PROMPT, question=QUESTION)

    assert reply == MODEL_REPLY


def test_sends_the_system_prompt_as_the_first_message(
    ask_question: AskQuestion, fake_language_model: FakeLanguageModel
) -> None:
    ask_question.execute(system_prompt=SYSTEM_PROMPT, question=QUESTION)

    assert fake_language_model.received_messages[0] == ChatMessage(Role.SYSTEM, SYSTEM_PROMPT)


def test_sends_the_question_as_a_user_message(
    ask_question: AskQuestion, fake_language_model: FakeLanguageModel
) -> None:
    ask_question.execute(system_prompt=SYSTEM_PROMPT, question=QUESTION)

    assert fake_language_model.received_messages[1] == ChatMessage(Role.USER, QUESTION)


def test_propagates_the_error_when_the_model_is_offline() -> None:
    ask_question = AskQuestion(OfflineLanguageModel())

    with pytest.raises(LanguageModelError):
        ask_question.execute(system_prompt=SYSTEM_PROMPT, question=QUESTION)
