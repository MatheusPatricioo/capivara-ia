import json
from collections.abc import Sequence

import pytest
from opentelemetry.trace import StatusCode

from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    StructuredReply,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from src.infrastructure.traced_language_model import TracedLanguageModel
from tests.fakes.recorded_spans import RecordedSpans

MODEL_NAME = "qwen2.5:7b"
MESSAGES = [
    ChatMessage(Role.SYSTEM, "Você é uma capivara."),
    ChatMessage(Role.USER, "O que vai pesquisar?"),
]
WEB_SEARCH = ToolDefinition("web_search", "Pesquisa na internet.", {"type": "object"})
SEARCH_CALL = ToolCall("web_search", {"query": "estrelas"})
CHAT_REPLY = ChatMessage(
    Role.ASSISTANT,
    "Vou pesquisar estrelas.",
    tool_calls=(SEARCH_CALL,),
    token_count=1280,
    usage=TokenUsage(input_tokens=1200, output_tokens=80),
)
STRUCTURED_REPLY = StructuredReply(
    data={"category": "cat"}, token_count=320, usage=TokenUsage(300, 20)
)
SCHEMA: dict[str, object] = {"type": "object"}
MODEL_PARAMETERS = {"temperature": 0.8, "num_ctx": 8192}


class FixedLanguageModel:
    def __init__(self, chat_reply: ChatMessage = CHAT_REPLY) -> None:
        self._chat_reply = chat_reply

    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        return self._chat_reply

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        return STRUCTURED_REPLY


class OfflineLanguageModel:
    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        raise LanguageModelError("Ollama is not running")

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        raise LanguageModelError("Ollama is not running")


@pytest.fixture
def recorded_spans() -> RecordedSpans:
    return RecordedSpans()


def traced(
    language_model: FixedLanguageModel | OfflineLanguageModel, recorded_spans: RecordedSpans
) -> TracedLanguageModel:
    return TracedLanguageModel(
        language_model,
        model_name=MODEL_NAME,
        provider_name="ollama",
        model_parameters=MODEL_PARAMETERS,
        tracer=recorded_spans.tracer,
    )


@pytest.fixture
def traced_model(recorded_spans: RecordedSpans) -> TracedLanguageModel:
    return traced(FixedLanguageModel(), recorded_spans)


def chat_attributes(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> dict[str, object]:
    traced_model.chat(MESSAGES, [WEB_SEARCH])
    return dict(recorded_spans.named(f"chat {MODEL_NAME}").attributes or {})


def test_returns_the_reply_of_the_model_unchanged(traced_model: TracedLanguageModel) -> None:
    assert traced_model.chat(MESSAGES, [WEB_SEARCH]) == CHAT_REPLY


def test_records_one_span_named_after_the_call_and_the_model(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    traced_model.chat(MESSAGES)

    assert recorded_spans.names() == [f"chat {MODEL_NAME}"]


def test_marks_the_span_as_a_generation_of_the_model(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    attributes = chat_attributes(traced_model, recorded_spans)

    assert attributes["langfuse.observation.type"] == "generation"
    assert attributes["gen_ai.request.model"] == MODEL_NAME
    assert attributes["gen_ai.system"] == "ollama"


def test_records_the_messages_it_read_as_a_chat(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    attributes = chat_attributes(traced_model, recorded_spans)

    assert json.loads(str(attributes["langfuse.observation.input"])) == [
        {"role": "system", "content": "Você é uma capivara."},
        {"role": "user", "content": "O que vai pesquisar?"},
    ]


def test_records_the_reply_with_its_tool_calls(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    attributes = chat_attributes(traced_model, recorded_spans)

    assert json.loads(str(attributes["langfuse.observation.output"])) == {
        "role": "assistant",
        "content": "Vou pesquisar estrelas.",
        "tool_calls": [
            {
                "type": "function",
                "function": {"name": "web_search", "arguments": '{"query": "estrelas"}'},
            }
        ],
    }


def test_records_the_tokens_read_and_written(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    attributes = chat_attributes(traced_model, recorded_spans)

    assert attributes["gen_ai.usage.input_tokens"] == 1200
    assert attributes["gen_ai.usage.output_tokens"] == 80


def test_records_the_total_when_the_model_does_not_split_the_tokens(
    recorded_spans: RecordedSpans,
) -> None:
    unsplit_reply = ChatMessage(Role.ASSISTANT, "Oi.", token_count=500)
    traced_model = traced(FixedLanguageModel(unsplit_reply), recorded_spans)

    attributes = chat_attributes(traced_model, recorded_spans)

    assert attributes["langfuse.observation.metadata.token_count"] == 500
    assert "gen_ai.usage.input_tokens" not in attributes


def test_records_the_tools_offered_to_the_model(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    attributes = chat_attributes(traced_model, recorded_spans)

    assert attributes["langfuse.observation.metadata.tools"] == "web_search"


def test_records_the_model_parameters(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    attributes = chat_attributes(traced_model, recorded_spans)

    assert json.loads(str(attributes["langfuse.observation.model.parameters"])) == MODEL_PARAMETERS


def test_a_failed_call_ends_its_span_as_an_error(recorded_spans: RecordedSpans) -> None:
    traced_model = traced(OfflineLanguageModel(), recorded_spans)

    with pytest.raises(LanguageModelError):
        traced_model.chat(MESSAGES)

    span = recorded_spans.named(f"chat {MODEL_NAME}")
    assert span.status.status_code == StatusCode.ERROR
    assert [event.name for event in span.events] == ["exception"]


def test_a_structured_call_records_the_parsed_reply_and_its_tokens(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    traced_model.complete_json(MESSAGES, SCHEMA)

    attributes = dict(recorded_spans.named(f"complete_json {MODEL_NAME}").attributes or {})
    assert json.loads(str(attributes["langfuse.observation.output"])) == {"category": "cat"}
    assert attributes["gen_ai.usage.input_tokens"] == 300


def test_a_call_inside_an_open_span_becomes_its_child(
    traced_model: TracedLanguageModel, recorded_spans: RecordedSpans
) -> None:
    with recorded_spans.tracer.start_as_current_span("autonomous_cycle"):
        traced_model.chat(MESSAGES)

    model_span = recorded_spans.named(f"chat {MODEL_NAME}")
    cycle_span = recorded_spans.named("autonomous_cycle")
    assert model_span.parent is not None
    assert model_span.parent.span_id == cycle_span.context.span_id
