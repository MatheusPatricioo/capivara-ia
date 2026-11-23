from collections.abc import Sequence
from dataclasses import asdict, dataclass

import httpx

from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    ToolCall,
    ToolDefinition,
)

UNEXPECTED_FORMAT_MESSAGE = "Unexpected response format from Ollama"


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
    ) -> None:
        self._client = client
        self._model = model
        self._generation_options = generation_options

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [self._serialize_message(message) for message in messages],
            "stream": False,
        }
        if tools:
            payload["tools"] = [self._serialize_tool(tool) for tool in tools]
        if self._generation_options is not None:
            payload["options"] = asdict(self._generation_options)
        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise LanguageModelError(f"Could not get a reply from Ollama: {error}") from error
        return self._parse_reply(response)

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
