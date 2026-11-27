from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager

from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind, Tracer

from src.application import tracing
from src.application.metered_language_model import ChattingAndStructuredLanguageModel
from src.domain.language_model import (
    ChatMessage,
    StructuredReply,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)


class TracedLanguageModel:
    """Decorator that records every model call as an OpenTelemetry span: the messages it
    read, what it answered, the tokens and the time. The span is a child of whatever span
    is open (a cycle, a conversation turn), so a trace shows the whole thought.

    A failing call ends its span as an error, with the exception attached, and the
    exception goes on to the caller unchanged.
    """

    def __init__(
        self,
        language_model: ChattingAndStructuredLanguageModel,
        model_name: str,
        provider_name: str,
        model_parameters: Mapping[str, object] | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._language_model = language_model
        self._model_name = model_name
        self._provider_name = provider_name
        self._model_parameters = dict(model_parameters or {})
        self._tracer = tracer or trace.get_tracer(__name__)

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        with self._start_generation("chat") as span:
            # Without tracing installed the span records nothing: skip building the JSON.
            if span.is_recording():
                tracing.record_input(span, [_as_chat_entry(message) for message in messages])
                if tools:
                    tools_offered = ", ".join(tool.name for tool in tools)
                    tracing.record_metadata(span, "tools", tools_offered)
            reply = self._language_model.chat(messages, tools)
            if span.is_recording():
                tracing.record_output(span, _as_chat_entry(reply))
            self._record_usage(span, reply.usage, reply.token_count)
            return reply

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        with self._start_generation("complete_json") as span:
            if span.is_recording():
                tracing.record_input(span, [_as_chat_entry(message) for message in messages])
                tracing.record_metadata(span, "response_schema", tracing.to_json(schema))
            reply = self._language_model.complete_json(messages, schema)
            if span.is_recording():
                tracing.record_output(span, reply.data)
            self._record_usage(span, reply.usage, reply.token_count)
            return reply

    def _start_generation(self, call_name: str) -> AbstractContextManager[Span]:
        return self._tracer.start_as_current_span(
            f"{call_name} {self._model_name}",
            kind=SpanKind.CLIENT,
            attributes=self._generation_attributes(),
        )

    def _generation_attributes(self) -> dict[str, str]:
        attributes = {
            tracing.OBSERVATION_TYPE: tracing.GENERATION,
            tracing.OPERATION_NAME: "chat",
            tracing.PROVIDER_NAME: self._provider_name,
            tracing.REQUEST_MODEL: self._model_name,
        }
        if self._model_parameters:
            attributes[tracing.MODEL_PARAMETERS] = tracing.to_json(self._model_parameters)
        return attributes

    @staticmethod
    def _record_usage(span: Span, usage: TokenUsage | None, token_count: int) -> None:
        """Read and written tokens when the model splits them; the total otherwise."""
        if usage is not None:
            span.set_attribute(tracing.INPUT_TOKENS, usage.input_tokens)
            span.set_attribute(tracing.OUTPUT_TOKENS, usage.output_tokens)
        elif token_count:
            tracing.record_metadata(span, "token_count", token_count)


def _as_chat_entry(message: ChatMessage) -> dict[str, object]:
    """A message in the role/content shape tracing panels show as a chat."""
    entry: dict[str, object] = {"role": message.role.value, "content": message.content}
    if message.tool_name is not None:
        entry["name"] = message.tool_name
    if message.tool_calls:
        entry["tool_calls"] = [_as_tool_call_entry(tool_call) for tool_call in message.tool_calls]
    return entry


def _as_tool_call_entry(tool_call: ToolCall) -> dict[str, object]:
    return {
        "type": "function",
        "function": {"name": tool_call.name, "arguments": tracing.to_json(tool_call.arguments)},
    }
