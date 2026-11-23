"""A whole autonomous cycle with what she noticed, using a fake language model."""

from collections.abc import Sequence

import pytest

from src.application.attention_inbox import AttentionInbox
from src.application.autonomous_loop import AutonomousLoop
from src.application.conversation import Conversation
from src.application.inner_voice import InnerVoice
from src.application.token_budget import HourlyTokenBudget
from src.domain.attention import Attention
from src.domain.discovery import DiscoveryHeadline
from src.domain.language_model import ChatMessage, LanguageModelError, Role, ToolDefinition
from src.infrastructure.prompt_loader import load_prompt

THOUGHT = "Fiquei pensando nas vitórias-régias, mas hoje vou só olhar o céu."
LILIES_DESCRIPTION = "vitórias-régias boiando no laguinho"


class RecordingLanguageModel:
    """Answers with a fixed thought and keeps every message it received."""

    def __init__(self) -> None:
        self.received_messages: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.received_messages.append(messages)
        return ChatMessage(Role.ASSISTANT, THOUGHT)


class OfflineLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        raise LanguageModelError("Ollama is not running")


class EmptyCatalog:
    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        return []


@pytest.fixture
def attention() -> AttentionInbox:
    inbox = AttentionInbox(Attention(capacity=5, rest_seconds=600.0))
    inbox.notice("water_lilies", LILIES_DESCRIPTION)
    return inbox


def build_loop(
    language_model: RecordingLanguageModel | OfflineLanguageModel, attention: AttentionInbox
) -> AutonomousLoop:
    inner_voice = InnerVoice(
        invitation=load_prompt("autonomous_cycle"),
        catalog=EmptyCatalog(),
        memory_template=load_prompt("known_discoveries"),
        max_remembered_discoveries=5,
        attention=attention,
        noticed_template=load_prompt("noticed_things"),
    )
    return AutonomousLoop(
        lambda: Conversation(language_model, "Você é uma capivara."),
        HourlyTokenBudget(10_000),
        inner_voice.compose,
        interval_seconds=1.0,
        on_cycle_finished=inner_voice.release_offered,
    )


def test_she_hears_about_what_she_noticed_in_her_cycle(attention: AttentionInbox) -> None:
    language_model = RecordingLanguageModel()

    build_loop(language_model, attention).run_cycle()

    inner_voice_message = language_model.received_messages[0][-1].content
    assert f"- {LILIES_DESCRIPTION}" in inner_voice_message


def test_what_she_noticed_is_let_go_after_the_cycle(attention: AttentionInbox) -> None:
    build_loop(RecordingLanguageModel(), attention).run_cycle()

    assert attention.pending() == ()


def test_what_she_noticed_keeps_waiting_when_the_cycle_fails(attention: AttentionInbox) -> None:
    build_loop(OfflineLanguageModel(), attention).run_cycle()

    assert [point.thing_id for point in attention.pending()] == ["water_lilies"]
