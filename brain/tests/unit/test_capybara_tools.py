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


def test_offers_only_search_and_save_because_drawing_is_automatic(
    settings: Settings, http_client: httpx.Client
) -> None:
    tools = build_capybara_tools(
        settings, Chalkboard(3), NeverAskedStructuredLanguageModel(), http_client
    )

    assert [tool.definition.name for tool in tools] == ["web_search", "save_discovery"]


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
