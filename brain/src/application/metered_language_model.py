from collections.abc import Sequence
from typing import Protocol

from src.application.token_budget import HourlyTokenBudget
from src.domain.language_model import (
    ChatMessage,
    LanguageModel,
    StructuredLanguageModel,
    StructuredReply,
    ToolDefinition,
)


class ChattingAndStructuredLanguageModel(LanguageModel, StructuredLanguageModel, Protocol):
    """A model that can both chat with tools and answer in a JSON shape."""


class MeteredLanguageModel:
    """Decorator that records the tokens of every reply in the hourly budget."""

    def __init__(
        self, language_model: ChattingAndStructuredLanguageModel, budget: HourlyTokenBudget
    ) -> None:
        self._language_model = language_model
        self._budget = budget

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        reply = self._language_model.chat(messages, tools)
        self._budget.record(reply.token_count)
        return reply

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        reply = self._language_model.complete_json(messages, schema)
        self._budget.record(reply.token_count)
        return reply
