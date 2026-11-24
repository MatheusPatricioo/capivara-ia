"""A discovery saved during a conversation ends up both in its file and in the memory."""

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from src.application.conversation import Conversation
from src.application.remembering_discovery_repository import RememberingDiscoveryRepository
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.seen_sources import SeenSources
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemoryError, RememberedDiscovery
from src.domain.language_model import ChatMessage, Role, ToolCall, ToolDefinition
from src.domain.tool import Tool
from src.domain.web_search import SearchResult
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder

TODAY = date(2026, 11, 24)
EXPECTED_FILE_NAME = "2026-11-24-capivaras-nadam.md"
SEARCHED_URL = "https://example.com/swim"
SAVE_REQUEST = ToolCall(
    name="save_discovery",
    arguments={
        "title": "Capivaras nadam",
        "topic": "capivaras",
        "summary": "Capivaras prendem a respiração por cinco minutos",
        "sources": [SEARCHED_URL],
    },
)


class FakeWebSearcher:
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        return [SearchResult(title="Capybaras swim", url=SEARCHED_URL, snippet="They dive.")]


class ScriptedLanguageModel:
    """Searches, saves a discovery, then gives the final answer."""

    def __init__(self) -> None:
        search_request = ToolCall(name="web_search", arguments={"query": "capybaras swim"})
        self._replies = iter(
            [
                ChatMessage(Role.ASSISTANT, "", tool_calls=(search_request,)),
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SAVE_REQUEST,)),
                ChatMessage(Role.ASSISTANT, "Guardei!"),
            ]
        )

    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        return next(self._replies)


class OfflineDiscoveryMemory:
    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise DiscoveryMemoryError("database offline")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        raise DiscoveryMemoryError("database offline")


def build_conversation(repository: RememberingDiscoveryRepository) -> Conversation:
    seen_sources = SeenSources()
    tools: list[Tool] = [
        WebSearchTool(FakeWebSearcher(), seen_sources=seen_sources),
        SaveDiscoveryTool(repository, seen_sources, today=lambda: TODAY),
    ]
    return Conversation(ScriptedLanguageModel(), "You are a curious capybara.", tools=tools)


@pytest.fixture
def memory() -> InMemoryDiscoveryMemory:
    return InMemoryDiscoveryMemory(WordCountEmbedder(["capivaras", "respiração"]))


@pytest.fixture
def conversation(memory: InMemoryDiscoveryMemory, tmp_path: Path) -> Conversation:
    repository = RememberingDiscoveryRepository(MarkdownDiscoveryRepository(tmp_path), memory)
    return build_conversation(repository)


@pytest.fixture
def conversation_with_offline_memory(tmp_path: Path) -> Conversation:
    repository = RememberingDiscoveryRepository(
        MarkdownDiscoveryRepository(tmp_path), OfflineDiscoveryMemory()
    )
    return build_conversation(repository)


def test_the_saved_discovery_can_be_recalled_by_meaning(
    conversation: Conversation, memory: InMemoryDiscoveryMemory
) -> None:
    conversation.send("Capivaras nadam?")

    [remembered] = memory.recall("capivaras e respiração", limit=1)
    assert remembered.discovery.title == "Capivaras nadam"


def test_the_discovery_file_is_written_even_when_the_memory_is_offline(
    conversation_with_offline_memory: Conversation, tmp_path: Path
) -> None:
    conversation_with_offline_memory.send("Capivaras nadam?")

    assert (tmp_path / EXPECTED_FILE_NAME).exists()


def test_the_conversation_ends_normally_when_the_memory_is_offline(
    conversation_with_offline_memory: Conversation,
) -> None:
    assert conversation_with_offline_memory.send("Capivaras nadam?") == "Guardei!"
