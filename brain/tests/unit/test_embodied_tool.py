import pytest

from src.application.tools.embodied_tool import EmbodiedTool
from src.domain.body import Place
from src.domain.drawing import Drawing
from src.domain.language_model import ToolDefinition
from src.domain.tool import ToolError

ECHO_DEFINITION = ToolDefinition(
    name="echo",
    description="Repeats the text.",
    parameters={"type": "object", "properties": {"text": {"type": "string"}}},
)


class RecordingBody:
    """Writes every body action in a shared timeline, so tests can check the order."""

    def __init__(self, timeline: list[str]) -> None:
        self._timeline = timeline

    def go_to(self, place: Place) -> None:
        self._timeline.append(f"go_to {place.value}")

    def show_chalkboard(self, drawings: tuple[Drawing, ...]) -> None:
        self._timeline.append("show_chalkboard")


class EchoTool:
    def __init__(self, timeline: list[str]) -> None:
        self._timeline = timeline

    @property
    def definition(self) -> ToolDefinition:
        return ECHO_DEFINITION

    def run(self, arguments: dict[str, object]) -> str:
        self._timeline.append("run echo")
        return f"echo: {arguments['text']}"


class FailingTool(EchoTool):
    def run(self, arguments: dict[str, object]) -> str:
        raise ToolError("could not echo")


@pytest.fixture
def timeline() -> list[str]:
    return []


@pytest.fixture
def embodied_echo(timeline: list[str]) -> EmbodiedTool:
    return EmbodiedTool(EchoTool(timeline), RecordingBody(timeline), Place.COMPUTER)


def test_keeps_the_wrapped_tool_definition(embodied_echo: EmbodiedTool) -> None:
    assert embodied_echo.definition == ECHO_DEFINITION


def test_returns_the_wrapped_tool_result(embodied_echo: EmbodiedTool) -> None:
    assert embodied_echo.run({"text": "oi"}) == "echo: oi"


def test_walks_to_the_place_before_running_the_tool(
    embodied_echo: EmbodiedTool, timeline: list[str]
) -> None:
    embodied_echo.run({"text": "oi"})

    assert timeline == ["go_to computer", "run echo"]


def test_lets_the_wrapped_tool_error_reach_the_model(timeline: list[str]) -> None:
    tool = EmbodiedTool(FailingTool(timeline), RecordingBody(timeline), Place.COMPUTER)

    with pytest.raises(ToolError, match="could not echo"):
        tool.run({"text": "oi"})
