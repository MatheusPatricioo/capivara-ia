from collections.abc import Sequence

from src.application.token_budget import HourlyTokenBudget
from src.domain.language_model import (
    ChatMessage,
    LanguageModel,
    ToolDefinition,
)


class MeteredLanguageModel:
    """Decorator that records the tokens of every reply in the hourly budget."""

    def __init__(
        self, language_model: LanguageModel, budget: HourlyTokenBudget
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
