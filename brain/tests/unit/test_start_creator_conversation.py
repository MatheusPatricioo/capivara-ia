from collections.abc import Iterator, Sequence
from pathlib import Path

import httpx
import pytest

from src.capybara_chat import start_creator_conversation
from src.domain.discovery import Discovery
from src.domain.discovery_memory import RememberedDiscovery
from src.domain.language_model import ChatMessage, Role, StructuredReply, ToolDefinition
from src.infrastructure.settings import Settings


class SilentLanguageModel:
    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        return ChatMessage(Role.ASSISTANT, "Oi!")

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        return StructuredReply(data={})


class EmptyMemory:
    def remember(self, file_name: str, discovery: Discovery) -> None:
        pass

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        return []


@pytest.fixture
def http_client() -> Iterator[httpx.Client]:
    with httpx.Client() as client:
        yield client


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, discoveries_dir=tmp_path, memory_recall_tool=True)


def test_in_a_chat_she_can_only_search_and_remember(
    settings: Settings, http_client: httpx.Client
) -> None:
    conversation = start_creator_conversation(
        settings, SilentLanguageModel(), http_client, EmptyMemory(), heart=None
    )
    conversation.send("Oi!")

    assert conversation.tool_names == {"web_search", "recall_memory"}


def test_the_chat_prompt_asks_for_short_spoken_replies(
    settings: Settings, http_client: httpx.Client
) -> None:
    conversation = start_creator_conversation(
        settings, SilentLanguageModel(), http_client, EmptyMemory(), heart=None
    )

    assert "uma a três frases curtas" in conversation.history[0].content
