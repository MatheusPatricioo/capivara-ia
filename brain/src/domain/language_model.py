from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, object]


@dataclass(frozen=True)
class TokenUsage:
    """Tokens one model call read (the prompt) and wrote (the reply)."""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_name: str | None = None
    token_count: int = 0
    """Tokens the model read and wrote to produce this reply (0 when unknown)."""
    usage: TokenUsage | None = None
    """The same tokens split into read and written, when the model reports them."""


class LanguageModelError(Exception):
    """Raised when the language model cannot produce a reply."""


class LanguageModel(Protocol):
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage: ...


@dataclass(frozen=True)
class StructuredReply:
    """A reply forced into the JSON shape of a schema, already parsed."""

    data: dict[str, object]
    token_count: int = 0
    """Tokens the model read and wrote to produce this reply (0 when unknown)."""
    usage: TokenUsage | None = None
    """The same tokens split into read and written, when the model reports them."""


class StructuredLanguageModel(Protocol):
    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        """Answers with a JSON object that follows the given JSON Schema."""
        ...
