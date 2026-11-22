import logging
from collections.abc import Sequence

import pytest

from src.application.conversation import Conversation, StepLimitReachedError
from src.domain.language_model import ChatMessage, Role, ToolCall, ToolDefinition

SYSTEM_PROMPT = "You are a curious capybara."
QUESTION = "How long do turtles live?"
FINAL_ANSWER = "Some live over a hundred years."
SEARCH_CALL = ToolCall(name="web_search", arguments={"query": "turtle lifespan"})
MAX_STEPS = 3
CONVERSATION_LOGGER = "src.application.conversation"


class FakeSearchTool:
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="web_search", description="Searches the web.", parameters={})

    def run(self, arguments: dict[str, object]) -> str:
        return "Turtles can live over 100 years."


class ScriptedLanguageModel:
    def __init__(self, replies: list[ChatMessage]) -> None:
        self._replies = iter(replies)

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        return next(self._replies)


class EndlessToolCallingLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        return ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_CALL,))


@pytest.fixture
def info_logs(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.INFO, logger=CONVERSATION_LOGGER)
    return caplog


@pytest.fixture
def searching_conversation() -> Conversation:
    language_model = ScriptedLanguageModel(
        [
            ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_CALL,)),
            ChatMessage(Role.ASSISTANT, FINAL_ANSWER),
        ]
    )
    return Conversation(
        language_model,
        SYSTEM_PROMPT,
        tools=[FakeSearchTool()],
        max_steps=MAX_STEPS,
    )


@pytest.fixture
def endless_conversation() -> Conversation:
    return Conversation(
        EndlessToolCallingLanguageModel(),
        SYSTEM_PROMPT,
        tools=[FakeSearchTool()],
        max_steps=MAX_STEPS,
    )


def test_logs_the_tool_name_arguments_and_step(
    searching_conversation: Conversation, info_logs: pytest.LogCaptureFixture
) -> None:
    searching_conversation.send(QUESTION)

    assert "Tool call at step 1/3: web_search {'query': 'turtle lifespan'}" in info_logs.messages


def test_logs_how_many_steps_the_answer_took(
    searching_conversation: Conversation, info_logs: pytest.LogCaptureFixture
) -> None:
    searching_conversation.send(QUESTION)

    assert "Answered in 2 step(s)" in info_logs.messages


def test_logs_a_warning_when_the_step_limit_is_reached(
    endless_conversation: Conversation, info_logs: pytest.LogCaptureFixture
) -> None:
    with pytest.raises(StepLimitReachedError):
        endless_conversation.send(QUESTION)

    assert info_logs.records[-1].levelname == "WARNING"
