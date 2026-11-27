import json
from collections.abc import Sequence

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import StatusCode

from src.application.conversation import Conversation, StepLimitReachedError
from src.domain.language_model import ChatMessage, Role, ToolCall, ToolDefinition
from src.domain.tool import ToolError
from tests.fakes.recorded_spans import RecordedSpans

SYSTEM_PROMPT = "Você é uma capivara."
QUESTION = "O que vai pesquisar?"
ANSWER = "Estrelas, achei lindo."
SEARCH_RESULT = "1. Estrelas - https://example.com/estrelas"
REMINDER = "Lembre de citar as fontes."
SEARCH_CALL = ToolCall("web_search", {"query": "estrelas"})


class ScriptedLanguageModel:
    """Answers with the given replies, one per call."""

    def __init__(self, replies: list[ChatMessage]) -> None:
        self._replies = iter(replies)

    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        return next(self._replies)


class SearchTool:
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition("web_search", "Pesquisa na internet.", {"type": "object"})

    def run(self, arguments: dict[str, object]) -> str:
        return SEARCH_RESULT


class BrokenSearchTool(SearchTool):
    def run(self, arguments: dict[str, object]) -> str:
        raise ToolError("search is offline")


def asks_for(tool_call: ToolCall) -> ChatMessage:
    return ChatMessage(Role.ASSISTANT, "", tool_calls=(tool_call,))


ANSWERS = ChatMessage(Role.ASSISTANT, ANSWER)


@pytest.fixture
def recorded_spans() -> RecordedSpans:
    return RecordedSpans()


def converse(
    recorded_spans: RecordedSpans,
    replies: list[ChatMessage],
    tool: SearchTool | None = None,
    max_steps: int = 5,
) -> Conversation:
    return Conversation(
        ScriptedLanguageModel(replies),
        SYSTEM_PROMPT,
        tools=[tool or SearchTool()],
        max_steps=max_steps,
        tool_result_reminder=REMINDER,
        tracer=recorded_spans.tracer,
    )


def attributes_of(span: ReadableSpan) -> dict[str, object]:
    return dict(span.attributes or {})


def test_a_turn_is_one_agent_span_with_the_message_and_the_answer(
    recorded_spans: RecordedSpans,
) -> None:
    converse(recorded_spans, [ANSWERS]).send(QUESTION)

    attributes = attributes_of(recorded_spans.named("conversation_turn"))
    assert attributes["langfuse.observation.type"] == "agent"
    assert attributes["langfuse.observation.input"] == QUESTION
    assert attributes["langfuse.observation.output"] == ANSWER


def test_the_turn_span_counts_its_steps(recorded_spans: RecordedSpans) -> None:
    converse(recorded_spans, [asks_for(SEARCH_CALL), ANSWERS]).send(QUESTION)

    attributes = attributes_of(recorded_spans.named("conversation_turn"))
    assert attributes["langfuse.observation.metadata.steps"] == 2


def test_each_tool_call_is_a_child_span_of_the_turn(recorded_spans: RecordedSpans) -> None:
    converse(recorded_spans, [asks_for(SEARCH_CALL), ANSWERS]).send(QUESTION)

    tool_span = recorded_spans.named("execute_tool web_search")
    turn_span = recorded_spans.named("conversation_turn")
    assert tool_span.parent is not None
    assert tool_span.parent.span_id == turn_span.context.span_id


def test_the_tool_span_records_the_arguments_and_the_result_without_the_reminder(
    recorded_spans: RecordedSpans,
) -> None:
    converse(recorded_spans, [asks_for(SEARCH_CALL), ANSWERS]).send(QUESTION)

    attributes = attributes_of(recorded_spans.named("execute_tool web_search"))
    assert attributes["langfuse.observation.type"] == "tool"
    assert json.loads(str(attributes["gen_ai.tool.call.arguments"])) == {"query": "estrelas"}
    assert attributes["gen_ai.tool.call.result"] == SEARCH_RESULT


def test_a_failing_tool_marks_only_its_own_span_as_an_error(
    recorded_spans: RecordedSpans,
) -> None:
    converse(recorded_spans, [asks_for(SEARCH_CALL), ANSWERS], tool=BrokenSearchTool()).send(
        QUESTION
    )

    tool_span = recorded_spans.named("execute_tool web_search")
    assert tool_span.status.status_code == StatusCode.ERROR
    assert tool_span.status.description == "search is offline"
    assert recorded_spans.named("conversation_turn").status.status_code == StatusCode.UNSET


def test_an_unknown_tool_marks_its_span_as_an_error(recorded_spans: RecordedSpans) -> None:
    unknown_call = ToolCall("fly", {})

    converse(recorded_spans, [asks_for(unknown_call), ANSWERS]).send(QUESTION)

    assert recorded_spans.named("execute_tool fly").status.status_code == StatusCode.ERROR


def test_reaching_the_step_limit_ends_the_turn_span_as_an_error(
    recorded_spans: RecordedSpans,
) -> None:
    conversation = converse(recorded_spans, [asks_for(SEARCH_CALL)], max_steps=1)

    with pytest.raises(StepLimitReachedError):
        conversation.send(QUESTION)

    turn_span = recorded_spans.named("conversation_turn")
    assert turn_span.status.status_code == StatusCode.ERROR
    assert [event.name for event in turn_span.events] == ["exception"]
