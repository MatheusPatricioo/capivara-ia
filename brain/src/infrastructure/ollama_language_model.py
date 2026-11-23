import json
import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace

import httpx

from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    StructuredReply,
    ToolCall,
    ToolDefinition,
)
from src.infrastructure.text_tool_call_parser import find_tool_call_in_text

UNEXPECTED_FORMAT_MESSAGE = "Unexpected response format from Ollama"
NOT_A_JSON_OBJECT_MESSAGE = "Ollama did not answer with a JSON object"
# JSON answers are longer than a spoken reply (a drawing has many shapes), and a JSON cut
# by the token limit is useless, so they get their own, larger limit.
DEFAULT_STRUCTURED_NUM_PREDICT = 800

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OllamaGenerationOptions:
    """Sampling settings sent as Ollama's "options"; field names match the Ollama API."""

    num_predict: int
    temperature: float
    repeat_penalty: float


class OllamaLanguageModel:
    def __init__(
        self,
        client: httpx.Client,
        model: str,
        generation_options: OllamaGenerationOptions | None = None,
        structured_num_predict: int = DEFAULT_STRUCTURED_NUM_PREDICT,
    ) -> None:
        self._client = client
        self._model = model
        self._generation_options = generation_options
        self._structured_num_predict = structured_num_predict

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        payload = self._base_payload(messages)
        if tools:
            payload["tools"] = [self._serialize_tool(tool) for tool in tools]
        reply = self._parse_reply(self._post_chat(payload))
        if tools and not reply.tool_calls:
            return self._recover_tool_call_written_as_text(reply, tools)
        return reply

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        """Uses Ollama's "format": while generating, only text that fits the schema is allowed."""
        payload = self._base_payload(messages, num_predict=self._structured_num_predict)
        payload["format"] = schema
        reply = self._parse_reply(self._post_chat(payload))
        try:
            data = json.loads(reply.content)
        except json.JSONDecodeError as error:
            raise LanguageModelError(NOT_A_JSON_OBJECT_MESSAGE) from error
        if not isinstance(data, dict):
            raise LanguageModelError(NOT_A_JSON_OBJECT_MESSAGE)
        return StructuredReply(data=data, token_count=reply.token_count)

    def _base_payload(
        self, messages: list[ChatMessage], num_predict: int | None = None
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [self._serialize_message(message) for message in messages],
            "stream": False,
        }
        options = asdict(self._generation_options) if self._generation_options else {}
        if num_predict is not None:
            options["num_predict"] = num_predict
        if options:
            payload["options"] = options
        return payload

    def _post_chat(self, payload: dict[str, object]) -> httpx.Response:
        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise LanguageModelError(f"Could not get a reply from Ollama: {error}") from error
        return response

    @staticmethod
    def _recover_tool_call_written_as_text(
        reply: ChatMessage, tools: Sequence[ToolDefinition]
    ) -> ChatMessage:
        """Turns a tool call printed in the text into a real one, dropping the invented rest.

        Whatever the model wrote around the call is discarded: it is either noise from the
        broken template or a made-up continuation (fake results, fake saves).
        """
        tool_call = find_tool_call_in_text(reply.content, {tool.name for tool in tools})
        if tool_call is None:
            return reply
        logger.warning("Recovered a tool call written as text: %s", tool_call.name)
        return replace(reply, content="", tool_calls=(tool_call,))

    @staticmethod
    def _serialize_message(message: ChatMessage) -> dict[str, object]:
        serialized: dict[str, object] = {"role": message.role.value, "content": message.content}
        if message.tool_calls:
            serialized["tool_calls"] = [
                {"function": {"name": tool_call.name, "arguments": tool_call.arguments}}
                for tool_call in message.tool_calls
            ]
        if message.tool_name is not None:
            serialized["tool_name"] = message.tool_name
        return serialized

    @staticmethod
    def _serialize_tool(tool: ToolDefinition) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    @classmethod
    def _parse_reply(cls, response: httpx.Response) -> ChatMessage:
        try:
            body = response.json()
            message = body["message"]
            content = message["content"]
            raw_tool_calls = message.get("tool_calls") or []
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise LanguageModelError(UNEXPECTED_FORMAT_MESSAGE) from error
        if not isinstance(content, str) or not isinstance(raw_tool_calls, list):
            raise LanguageModelError(UNEXPECTED_FORMAT_MESSAGE)
        tool_calls = tuple(cls._parse_tool_call(raw_tool_call) for raw_tool_call in raw_tool_calls)
        return ChatMessage(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
            token_count=cls._token_count(body),
        )

    @staticmethod
    def _token_count(body: dict[str, object]) -> int:
        """Ollama reports read tokens (prompt_eval_count) and written tokens (eval_count)."""
        counts = (body.get("prompt_eval_count"), body.get("eval_count"))
        return sum(count for count in counts if isinstance(count, int))

    @staticmethod
    def _parse_tool_call(raw_tool_call: object) -> ToolCall:
        if not isinstance(raw_tool_call, dict):
            raise LanguageModelError(UNEXPECTED_FORMAT_MESSAGE)
        function = raw_tool_call.get("function")
        if not isinstance(function, dict):
            raise LanguageModelError(UNEXPECTED_FORMAT_MESSAGE)
        name = function.get("name")
        arguments = function.get("arguments")
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise LanguageModelError(UNEXPECTED_FORMAT_MESSAGE)
        return ToolCall(name=name, arguments=arguments)
