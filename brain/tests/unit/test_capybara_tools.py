from pathlib import Path

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


class RecordingBody:
    """Remembers every place the capybara was sent to."""

    def __init__(self) -> None:
        self.visited_places: list[Place] = []

    def go_to(self, place: Place) -> None:
        self.visited_places.append(place)

    def show_chalkboard(self, drawings: tuple[Drawing, ...]) -> None:
        pass


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, discoveries_dir=tmp_path)


def test_offers_only_search_and_save_because_drawing_is_automatic(settings: Settings) -> None:
    tools = build_capybara_tools(settings, Chalkboard(3), NeverAskedStructuredLanguageModel())

    assert [tool.definition.name for tool in tools] == ["web_search", "save_discovery"]


def test_goes_to_the_computer_to_save_a_discovery(settings: Settings) -> None:
    body = RecordingBody()
    tools = build_capybara_tools(
        settings, Chalkboard(3), NeverAskedStructuredLanguageModel(), body=body
    )
    save_discovery = next(tool for tool in tools if tool.definition.name == "save_discovery")

    with pytest.raises(ToolError):
        save_discovery.run({})

    assert body.visited_places == [Place.COMPUTER]
