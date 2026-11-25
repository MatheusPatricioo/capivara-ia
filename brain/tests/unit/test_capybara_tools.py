from pathlib import Path

import httpx
import pytest

from src.capybara_tools import build_capybara_tools
from src.domain.body import Place
from src.domain.chalkboard import Chalkboard
from src.domain.drawing import Drawing
from src.domain.language_model import ChatMessage, StructuredReply
from src.domain.tool import ToolError
from src.infrastructure.settings import Settings
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder
from tests.fakes.in_memory_emotional_memory import RecordingFeeler


class NeverAskedStructuredLanguageModel:
    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        raise AssertionError("building the tools must not call the model")


def never_called(request: httpx.Request) -> httpx.Response:
    raise AssertionError("building the tools must not call Ollama")


class RecordingBody:
    """Remembers every place the capybara was sent to."""

    def __init__(self) -> None:
        self.visited_places: list[Place] = []

    def go_to(self, place: Place) -> None:
        self.visited_places.append(place)

    def show_chalkboard(self, drawings: tuple[Drawing, ...]) -> None:
        pass


@pytest.fixture
def http_client() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(never_called), base_url="http://ollama")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, discoveries_dir=tmp_path)


def test_offers_search_save_and_suggest_but_no_draw_tool_because_drawing_is_automatic(
    settings: Settings, http_client: httpx.Client
) -> None:
    tools = build_capybara_tools(
        settings, Chalkboard(3), NeverAskedStructuredLanguageModel(), http_client
    )

    assert [tool.definition.name for tool in tools] == [
        "web_search",
        "save_discovery",
        "suggest_improvement",
    ]


def test_with_a_memory_but_the_recall_tool_off_she_gets_no_recall_tool(
    settings: Settings, http_client: httpx.Client
) -> None:
    memory = InMemoryDiscoveryMemory(WordCountEmbedder(["lua"]))
    tools = build_capybara_tools(
        settings, Chalkboard(3), NeverAskedStructuredLanguageModel(), http_client, memory=memory
    )

    assert "recall_memory" not in [tool.definition.name for tool in tools]


def test_with_a_memory_and_the_recall_tool_on_she_can_also_search_her_treasure(
    settings: Settings, http_client: httpx.Client
) -> None:
    settings = settings.model_copy(update={"memory_recall_tool": True})
    memory = InMemoryDiscoveryMemory(WordCountEmbedder(["lua"]))
    tools = build_capybara_tools(
        settings, Chalkboard(3), NeverAskedStructuredLanguageModel(), http_client, memory=memory
    )

    assert tools[-1].definition.name == "recall_memory"


def test_goes_to_the_computer_to_save_a_discovery(
    settings: Settings, http_client: httpx.Client
) -> None:
    body = RecordingBody()
    tools = build_capybara_tools(
        settings, Chalkboard(3), NeverAskedStructuredLanguageModel(), http_client, body=body
    )
    save_discovery = next(tool for tool in tools if tool.definition.name == "save_discovery")

    with pytest.raises(ToolError):
        save_discovery.run({})

    assert body.visited_places == [Place.COMPUTER]


def test_goes_to_the_computer_to_suggest_an_improvement(
    settings: Settings, http_client: httpx.Client
) -> None:
    body = RecordingBody()
    tools = build_capybara_tools(
        settings, Chalkboard(3), NeverAskedStructuredLanguageModel(), http_client, body=body
    )
    suggest = next(tool for tool in tools if tool.definition.name == "suggest_improvement")

    with pytest.raises(ToolError):
        suggest.run({})

    assert body.visited_places == [Place.COMPUTER]


def test_with_a_heart_she_keeps_the_same_tools(
    settings: Settings, http_client: httpx.Client
) -> None:
    tools = build_capybara_tools(
        settings,
        Chalkboard(3),
        NeverAskedStructuredLanguageModel(),
        http_client,
        heart=RecordingFeeler(),
    )

    assert [tool.definition.name for tool in tools] == [
        "web_search",
        "save_discovery",
        "suggest_improvement",
    ]
