from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from src.application.conversation import Conversation
from src.application.tools.draw_tool import DrawTool
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.saved_discoveries import SavedDiscoveries
from src.application.tools.seen_sources import SeenSources
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.chalkboard import Chalkboard
from src.domain.language_model import ChatMessage, Role, ToolCall, ToolDefinition
from src.domain.web_search import SearchResult
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.png_drawing_repository import PngDrawingRepository

SYSTEM_PROMPT = "You are a curious capybara."
USER_MESSAGE = "Capivaras nadam?"
FINAL_ANSWER = "Guardei e desenhei!"
TODAY = date(2026, 11, 23)
SEARCHED_URL = "https://example.com/swim"
EXPECTED_DRAWING_FILE = "2026-11-23-capivaras-nadam.png"
SEARCH_REQUEST = ToolCall(name="web_search", arguments={"query": "capybaras swim"})
SAVE_REQUEST = ToolCall(
    name="save_discovery",
    arguments={
        "title": "Capivaras nadam",
        "topic": "capivaras",
        "summary": "Eu prendo a respiração por cinco minutos!",
        "sources": [SEARCHED_URL],
    },
)
DRAW_REQUEST = ToolCall(
    name="draw",
    arguments={
        "discovery_title": "Capivaras nadam",
        "shapes": [
            {"type": "line", "x1": 0, "y1": 200, "x2": 400, "y2": 200, "color": "blue"},
            {"type": "circle", "x": 200, "y": 180, "radius": 30, "color": "pink"},
        ],
    },
)


class FakeWebSearcher:
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        return [SearchResult(title="Capybaras swim", url=SEARCHED_URL, snippet="Five minutes.")]


class ScriptedLanguageModel:
    """Searches, saves the discovery, draws it, then gives the final answer."""

    def __init__(self) -> None:
        self._replies = iter(
            [
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_REQUEST,)),
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SAVE_REQUEST,)),
                ChatMessage(Role.ASSISTANT, "", tool_calls=(DRAW_REQUEST,)),
                ChatMessage(Role.ASSISTANT, FINAL_ANSWER),
            ]
        )
        self.received_histories: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.received_histories.append(messages)
        return next(self._replies)


@pytest.fixture
def language_model() -> ScriptedLanguageModel:
    return ScriptedLanguageModel()


@pytest.fixture
def chalkboard() -> Chalkboard:
    return Chalkboard(capacity=3)


@pytest.fixture
def conversation(
    language_model: ScriptedLanguageModel, chalkboard: Chalkboard, tmp_path: Path
) -> Conversation:
    seen_sources = SeenSources()
    saved_discoveries = SavedDiscoveries()
    tools = [
        WebSearchTool(FakeWebSearcher(), seen_sources=seen_sources),
        SaveDiscoveryTool(
            MarkdownDiscoveryRepository(tmp_path),
            seen_sources,
            today=lambda: TODAY,
            saved_discoveries=saved_discoveries,
        ),
        DrawTool(
            PngDrawingRepository(tmp_path), chalkboard, saved_discoveries, today=lambda: TODAY
        ),
    ]
    return Conversation(language_model, SYSTEM_PROMPT, tools=tools, max_steps=5)


def test_writes_the_drawing_png_next_to_the_discovery(
    conversation: Conversation, tmp_path: Path
) -> None:
    conversation.send(USER_MESSAGE)

    assert (tmp_path / EXPECTED_DRAWING_FILE).exists()


def test_pins_the_drawing_on_the_chalkboard(
    conversation: Conversation, chalkboard: Chalkboard
) -> None:
    conversation.send(USER_MESSAGE)

    assert [drawing.title for drawing in chalkboard.drawings] == ["Capivaras nadam"]


def test_tells_the_model_the_drawing_was_pinned(
    conversation: Conversation, language_model: ScriptedLanguageModel
) -> None:
    conversation.send(USER_MESSAGE)

    tool_result = language_model.received_histories[3][-1]
    assert tool_result == ChatMessage(
        Role.TOOL,
        f"Drawn as {EXPECTED_DRAWING_FILE} and pinned on your chalkboard.",
        tool_name="draw",
    )


def test_returns_the_final_answer_after_drawing(conversation: Conversation) -> None:
    assert conversation.send(USER_MESSAGE) == FINAL_ANSWER
