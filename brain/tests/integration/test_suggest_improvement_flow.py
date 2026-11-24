from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from src.application.conversation import Conversation
from src.application.repeated_suggestions import RepeatedSuggestions
from src.application.tools.conversation_discoveries import ConversationDiscoveries
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.seen_sources import SeenSources
from src.application.tools.suggest_improvement_tool import SuggestImprovementTool
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.language_model import ChatMessage, Role, ToolCall, ToolDefinition
from src.domain.web_search import SearchResult
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from tests.fakes.in_memory_discovery_memory import WordCountEmbedder

SYSTEM_PROMPT = "You are a curious capybara."
INNER_VOICE = "O que você quer fazer agora?"
FINAL_ANSWER = "Pedi vaga-lumes para o meu jardim!"
TODAY = date(2026, 11, 24)
SEARCHED_URL = "https://example.com/fireflies"
EXPECTED_SUGGESTION_FILE = "2026-11-24-vaga-lumes-no-jardim.md"
SEARCH_REQUEST = ToolCall(name="web_search", arguments={"query": "vaga-lumes"})
SAVE_REQUEST = ToolCall(
    name="save_discovery",
    arguments={
        "title": "Vaga-lumes piscam para conversar",
        "topic": "insetos",
        "summary": "Cada piscada é um recado!",
        "sources": [SEARCHED_URL],
    },
)
SUGGEST_REQUEST = ToolCall(
    name="suggest_improvement",
    arguments={
        "request": "Vaga-lumes no jardim",
        "reason": "Quero ver os recados piscando à noite.",
    },
)


class FakeWebSearcher:
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        return [SearchResult(title="Fireflies", url=SEARCHED_URL, snippet="They blink.")]


class ScriptedLanguageModel:
    """Searches, saves a discovery, suggests something for her world, then answers."""

    def __init__(self) -> None:
        self._replies = iter(
            [
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_REQUEST,)),
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SAVE_REQUEST,)),
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SUGGEST_REQUEST,)),
                ChatMessage(Role.ASSISTANT, FINAL_ANSWER),
            ]
        )
        self.received_histories: list[list[ChatMessage]] = []

    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        self.received_histories.append(messages)
        return next(self._replies)


@pytest.fixture
def language_model() -> ScriptedLanguageModel:
    return ScriptedLanguageModel()


@pytest.fixture
def conversation(language_model: ScriptedLanguageModel, tmp_path: Path) -> Conversation:
    """The same wiring as build_capybara_tools, with fakes for the web and the embeddings."""
    seen_sources = SeenSources()
    saved_discoveries = ConversationDiscoveries()
    suggestions = MarkdownSuggestionRepository(tmp_path)
    tools = [
        WebSearchTool(FakeWebSearcher(), seen_sources=seen_sources),
        SaveDiscoveryTool(
            MarkdownDiscoveryRepository(tmp_path),
            seen_sources,
            today=lambda: TODAY,
            saved_discoveries=saved_discoveries,
        ),
        SuggestImprovementTool(
            suggestions,
            RepeatedSuggestions(suggestions, WordCountEmbedder(["vaga-lumes", "jardim"]), 0.80),
            saved_discoveries,
            today=lambda: TODAY,
        ),
    ]
    return Conversation(language_model, SYSTEM_PROMPT, tools=tools)


def test_writes_the_suggestion_inspired_by_the_discovery_she_just_saved(
    conversation: Conversation, tmp_path: Path
) -> None:
    conversation.send(INNER_VOICE)

    content = (tmp_path / "sugestoes" / EXPECTED_SUGGESTION_FILE).read_text(encoding="utf-8")
    assert "- **Inspirada em:** Vaga-lumes piscam para conversar" in content


def test_keeps_the_suggestion_apart_from_the_discoveries(
    conversation: Conversation, tmp_path: Path
) -> None:
    conversation.send(INNER_VOICE)

    discoveries = MarkdownDiscoveryRepository(tmp_path).saved_file_names()
    assert discoveries == ["2026-11-24-vaga-lumes-piscam-para-conversar.md"]


def test_tells_the_model_the_suggestion_was_saved(
    conversation: Conversation, language_model: ScriptedLanguageModel
) -> None:
    conversation.send(INNER_VOICE)

    tool_result = language_model.received_histories[3][-1]
    assert tool_result.tool_name == "suggest_improvement"
    assert tool_result.content.startswith(f"Suggestion saved as {EXPECTED_SUGGESTION_FILE}.")


def test_returns_the_final_answer_after_suggesting(conversation: Conversation) -> None:
    assert conversation.send(INNER_VOICE) == FINAL_ANSWER
