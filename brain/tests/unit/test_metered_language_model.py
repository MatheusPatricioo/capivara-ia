from collections.abc import Sequence

from src.application.metered_language_model import MeteredLanguageModel
from src.application.token_budget import HourlyTokenBudget
from src.domain.language_model import ChatMessage, Role, ToolDefinition

REPLY = ChatMessage(Role.ASSISTANT, "Quero pesquisar estrelas.", token_count=420)
MESSAGES = [ChatMessage(Role.USER, "oi")]


class FixedLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        return REPLY


def test_returns_the_reply_of_the_wrapped_model() -> None:
    model = MeteredLanguageModel(FixedLanguageModel(), HourlyTokenBudget(1000))

    assert model.chat(MESSAGES) == REPLY


def test_records_the_reply_tokens_in_the_budget() -> None:
    budget = HourlyTokenBudget(1000)
    model = MeteredLanguageModel(FixedLanguageModel(), budget)

    model.chat(MESSAGES)

    assert budget.tokens_used_in_the_last_hour == 420
