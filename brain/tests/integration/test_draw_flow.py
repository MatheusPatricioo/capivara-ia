from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from src.application.category_matcher import CategoryMatch
from src.application.chalkboard_artist import ChalkboardArtist
from src.application.conversation import Conversation
from src.application.illustrate_discovery import IllustrateDiscovery
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.seen_sources import SeenSources
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.chalkboard import Chalkboard
from src.domain.doodle import Doodle, DoodleLibrary
from src.domain.language_model import (
    ChatMessage,
    Role,
    ToolCall,
    ToolDefinition,
)
from src.domain.web_search import SearchResult
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.png_drawing_repository import PngDrawingRepository

SYSTEM_PROMPT = "You are a curious capybara."
USER_MESSAGE = "Capivaras nadam?"
FINAL_ANSWER = "Guardei e desenhei!"
TODAY = date(2026, 11, 23)
SEARCHED_URL = "https://example.com/swim"
EXPECTED_DISCOVERY_FILE = "2026-11-23-capivaras-nadam.md"
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
WAVES_DOODLE = Doodle(
    category="ocean",
    strokes=(((0, 100), (60, 80), (120, 100)), ((0, 150), (60, 130)), ((0, 200), (60, 180))),
)


class FakeWebSearcher:
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        return [SearchResult(title="Capybaras swim", url=SEARCHED_URL, snippet="Five minutes.")]


class ScriptedLanguageModel:
    """Searches, saves the discovery, then answers."""

    def __init__(self) -> None:
        self._replies = iter(
            [
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_REQUEST,)),
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SAVE_REQUEST,)),
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


class OceanFinder:
    """Stands in for the embeddings: every discovery is clearly about the ocean."""

    def closest(self, text: str) -> CategoryMatch:
        return CategoryMatch(category="ocean", similarity=0.8, margin=0.1)


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
    illustrator = IllustrateDiscovery(
        OceanFinder(),
        DoodleLibrary({"ocean": [WAVES_DOODLE]}),
        ChalkboardArtist(PngDrawingRepository(tmp_path), chalkboard, today=lambda: TODAY),
        min_margin=0.02,
    )
    tools = [
        WebSearchTool(FakeWebSearcher(), seen_sources=seen_sources),
        SaveDiscoveryTool(
            MarkdownDiscoveryRepository(tmp_path),
            seen_sources,
            today=lambda: TODAY,
            illustrate=illustrator.illustrate,
        ),
    ]
    return Conversation(language_model, SYSTEM_PROMPT, tools=tools, max_steps=5)


def test_writes_the_drawing_png_next_to_the_discovery(
    conversation: Conversation, tmp_path: Path
) -> None:
    conversation.send(USER_MESSAGE)

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        EXPECTED_DISCOVERY_FILE,
        EXPECTED_DRAWING_FILE,
    ]


def test_pins_the_drawing_on_the_chalkboard(
    conversation: Conversation, chalkboard: Chalkboard
) -> None:
    conversation.send(USER_MESSAGE)

    assert [drawing.title for drawing in chalkboard.drawings] == ["Capivaras nadam"]


def test_tells_the_model_the_discovery_was_saved_and_drawn(
    conversation: Conversation, language_model: ScriptedLanguageModel
) -> None:
    conversation.send(USER_MESSAGE)

    tool_result = language_model.received_histories[2][-1]
    assert tool_result == ChatMessage(
        Role.TOOL,
        f"Saved as {EXPECTED_DISCOVERY_FILE}. Then you walked to your chalkboard and drew it "
        f"with 3 chalk stroke(s), saved as {EXPECTED_DRAWING_FILE}.",
        tool_name="save_discovery",
    )


def test_returns_the_final_answer_after_drawing(conversation: Conversation) -> None:
    assert conversation.send(USER_MESSAGE) == FINAL_ANSWER
