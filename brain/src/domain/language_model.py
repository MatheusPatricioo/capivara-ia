from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


class LanguageModelError(Exception):
    """Raised when the language model cannot produce a reply."""


class LanguageModel(Protocol):
    def chat(self, messages: list[ChatMessage]) -> str: ...
