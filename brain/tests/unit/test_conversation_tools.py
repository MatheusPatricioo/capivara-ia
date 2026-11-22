from collections.abc import Sequence

import pytest

from src.application.conversation import Conversation, StepLimitReachedError
from src.domain.language_model import ChatMessage, Role, ToolCall, ToolDefinition
from src.domain.tool import ToolError

SYSTEM_PROMPT = "You are a curious capybara."
QUESTION = "How far is the Moon?"
FINAL_ANSWER = "About 384,000 km."
MOON_TOOL_CALL = ToolCall(name="echo", arguments={"text": "moon distance"})
UNKNOWN_TOOL_CALL = ToolCall(name="teleport", arguments={})
MAX_STEPS = 3


class EchoTool:
    def __init__(self) -> None:
        self.received_arguments: list[dict[str, object]] = []

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="echo",
            description="Repeats the given text.",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        )

    def run(self, arguments: dict[str, object]) -> str:
        self.received_arguments.append(arguments)
        return f"echo: {arguments['text']}"


class BrokenTool:
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="echo", description="Always fails.", parameters={})

    def run(self, arguments: dict[str, object]) -> str:
        raise ToolError("the search engine is down")


class ScriptedLanguageModel:
    """Returns the scripted replies in order and records what it received."""

    def __init__(self, replies: list[ChatMessage]) -> None:
        self._replies = iter(replies)
        self.received_histories: list[list[ChatMessage]] = []
        self.received_tools: list[list[ToolDefinition]] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.received_histories.append(messages)
        self.received_tools.append(list(tools))
        return next(self._replies)


class EndlessToolCallingLanguageModel:
    """Never gives a final answer: always asks for the tool again."""

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        return ChatMessage(Role.ASSISTANT, "", tool_calls=(MOON_TOOL_CALL,))


def tool_request(tool_call: ToolCall) -> ChatMessage:
    return ChatMessage(Role.ASSISTANT, "", tool_calls=(tool_call,))


@pytest.fixture
def echo_tool() -> EchoTool:
    return EchoTool()


@pytest.fixture
def language_model_asking_for_echo() -> ScriptedLanguageModel:
    return ScriptedLanguageModel(
        [tool_request(MOON_TOOL_CALL), ChatMessage(Role.ASSISTANT, FINAL_ANSWER)]
    )


@pytest.fixture
def language_model_asking_for_unknown_tool() -> ScriptedLanguageModel:
    return ScriptedLanguageModel(
        [tool_request(UNKNOWN_TOOL_CALL), ChatMessage(Role.ASSISTANT, FINAL_ANSWER)]
    )


@pytest.fixture
def conversation_with_echo(
    language_model_asking_for_echo: ScriptedLanguageModel, echo_tool: EchoTool
) -> Conversation:
    return Conversation(language_model_asking_for_echo, SYSTEM_PROMPT, tools=[echo_tool])


@pytest.fixture
def endless_conversation(echo_tool: EchoTool) -> Conversation:
    return Conversation(
        EndlessToolCallingLanguageModel(),
        SYSTEM_PROMPT,
        tools=[echo_tool],
        max_steps=MAX_STEPS,
    )


def test_sends_the_tool_definitions_to_the_model(
    conversation_with_echo: Conversation,
    language_model_asking_for_echo: ScriptedLanguageModel,
    echo_tool: EchoTool,
) -> None:
    conversation_with_echo.send(QUESTION)

    assert language_model_asking_for_echo.received_tools[0] == [echo_tool.definition]


def test_runs_the_requested_tool_with_the_model_arguments(
    conversation_with_echo: Conversation, echo_tool: EchoTool
) -> None:
    conversation_with_echo.send(QUESTION)

    assert echo_tool.received_arguments == [{"text": "moon distance"}]


def test_returns_the_final_answer_after_the_tool_runs(
    conversation_with_echo: Conversation,
) -> None:
    reply = conversation_with_echo.send(QUESTION)

    assert reply == FINAL_ANSWER


def test_sends_the_tool_result_back_to_the_model(
    conversation_with_echo: Conversation,
    language_model_asking_for_echo: ScriptedLanguageModel,
) -> None:
    conversation_with_echo.send(QUESTION)

    assert language_model_asking_for_echo.received_histories[1][-2:] == [
        tool_request(MOON_TOOL_CALL),
        ChatMessage(Role.TOOL, "echo: moon distance", tool_name="echo"),
    ]


def test_history_keeps_the_tool_request_and_result(
    conversation_with_echo: Conversation,
) -> None:
    conversation_with_echo.send(QUESTION)

    assert conversation_with_echo.history == (
        ChatMessage(Role.SYSTEM, SYSTEM_PROMPT),
        ChatMessage(Role.USER, QUESTION),
        tool_request(MOON_TOOL_CALL),
        ChatMessage(Role.TOOL, "echo: moon distance", tool_name="echo"),
        ChatMessage(Role.ASSISTANT, FINAL_ANSWER),
    )


def test_tells_the_model_when_the_tool_does_not_exist(
    language_model_asking_for_unknown_tool: ScriptedLanguageModel,
) -> None:
    conversation = Conversation(language_model_asking_for_unknown_tool, SYSTEM_PROMPT)

    conversation.send(QUESTION)

    tool_result = language_model_asking_for_unknown_tool.received_histories[1][-1]
    assert tool_result == ChatMessage(
        Role.TOOL, "Error: unknown tool 'teleport'", tool_name="teleport"
    )


def test_tells_the_model_when_the_tool_fails(
    language_model_asking_for_echo: ScriptedLanguageModel,
) -> None:
    conversation = Conversation(language_model_asking_for_echo, SYSTEM_PROMPT, tools=[BrokenTool()])

    conversation.send(QUESTION)

    tool_result = language_model_asking_for_echo.received_histories[1][-1]
    assert tool_result.content == "Error: the search engine is down"


def test_raises_when_the_model_exceeds_the_step_limit(
    endless_conversation: Conversation,
) -> None:
    with pytest.raises(StepLimitReachedError):
        endless_conversation.send(QUESTION)


def test_stops_running_tools_at_the_step_limit(
    endless_conversation: Conversation, echo_tool: EchoTool
) -> None:
    with pytest.raises(StepLimitReachedError):
        endless_conversation.send(QUESTION)

    assert len(echo_tool.received_arguments) == MAX_STEPS


def test_keeps_history_unchanged_when_the_step_limit_is_reached(
    endless_conversation: Conversation,
) -> None:
    with pytest.raises(StepLimitReachedError):
        endless_conversation.send(QUESTION)

    assert endless_conversation.history == (ChatMessage(Role.SYSTEM, SYSTEM_PROMPT),)
