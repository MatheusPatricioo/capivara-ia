"""RAG in a whole autonomous cycle: what she noticed brings back what she already knows."""

from collections.abc import Sequence
from datetime import date

import pytest

from src.application.attention_inbox import AttentionInbox
from src.application.autonomous_loop import AutonomousLoop
from src.application.conversation import Conversation
from src.application.inner_voice import InnerVoice
from src.application.related_discoveries import RelatedDiscoveries
from src.application.token_budget import HourlyTokenBudget
from src.domain.attention import Attention
from src.domain.discovery import Discovery, DiscoveryHeadline
from src.domain.discovery_memory import DiscoveryMemory
from src.domain.language_model import ChatMessage, Role, ToolDefinition
from src.infrastructure.prompt_loader import load_prompt
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder

LILIES_DESCRIPTION = "vitórias-régias boiando no laguinho"
VICTORIA = Discovery(
    title="Vitória-régia",
    topic="plantas",
    summary="As folhas das vitórias-régias boiando aguentam peso",
    sources=("https://example.com/vitoria",),
    discovered_on=date(2026, 11, 24),
)
PIZZA = Discovery(
    title="História da pizza",
    topic="culinária",
    summary="A pizza margherita nasceu em Nápoles",
    sources=("https://example.com/pizza",),
    discovered_on=date(2026, 11, 24),
)


class RecordingLanguageModel:
    """Answers with a short thought and keeps the messages of every request."""

    def __init__(self) -> None:
        self.received_messages: list[list[ChatMessage]] = []

    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        self.received_messages.append(messages)
        return ChatMessage(Role.ASSISTANT, "Hoje só olhei as vitórias-régias.")


class EmptyCatalog:
    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        return []


@pytest.fixture
def memory() -> InMemoryDiscoveryMemory:
    vocabulary = ["vitórias-régias", "boiando", "laguinho", "pizza", "nápoles"]
    memory = InMemoryDiscoveryMemory(WordCountEmbedder(vocabulary))
    memory.remember("2026-11-24-vitoria-regia.md", VICTORIA)
    memory.remember("2026-11-24-historia-da-pizza.md", PIZZA)
    return memory


@pytest.fixture
def attention() -> AttentionInbox:
    inbox = AttentionInbox(Attention(capacity=5, rest_seconds=600.0))
    inbox.notice("water_lilies", LILIES_DESCRIPTION)
    return inbox


@pytest.fixture
def language_model() -> RecordingLanguageModel:
    return RecordingLanguageModel()


@pytest.fixture
def inner_voice_message(
    memory: DiscoveryMemory, attention: AttentionInbox, language_model: RecordingLanguageModel
) -> str:
    """Runs one cycle and returns the inner voice the capybara heard in it."""
    inner_voice = InnerVoice(
        invitation=load_prompt("autonomous_cycle"),
        catalog=EmptyCatalog(),
        memory_template=load_prompt("known_discoveries"),
        max_remembered_discoveries=5,
        attention=attention,
        noticed_template=load_prompt("noticed_things"),
        related=RelatedDiscoveries(memory, min_similarity=0.5),
        related_template=load_prompt("related_discoveries"),
    )
    loop = AutonomousLoop(
        lambda: Conversation(language_model, "Você é uma capivara."),
        HourlyTokenBudget(10_000),
        inner_voice.compose,
        interval_seconds=1.0,
        on_cycle_finished=inner_voice.release_offered,
    )
    loop.run_cycle()
    [first_request] = language_model.received_messages
    return first_request[-1].content


def test_she_remembers_the_discovery_related_to_what_she_noticed(
    inner_voice_message: str,
) -> None:
    assert f"- {VICTORIA.title}: {VICTORIA.summary}" in inner_voice_message


def test_she_does_not_remember_an_unrelated_discovery(inner_voice_message: str) -> None:
    assert PIZZA.title not in inner_voice_message


def test_what_she_remembers_comes_before_what_she_noticed(inner_voice_message: str) -> None:
    assert inner_voice_message.index(VICTORIA.title) < inner_voice_message.index(LILIES_DESCRIPTION)
