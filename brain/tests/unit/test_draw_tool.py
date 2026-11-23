from datetime import date

import pytest

from src.application.tools.draw_tool import DrawTool
from src.application.tools.saved_discoveries import SavedDiscoveries
from src.domain.body import Place
from src.domain.chalkboard import Chalkboard
from src.domain.drawing import Circle, Drawing, DrawingStorageError, Point
from src.domain.tool import ToolError

TODAY = date(2026, 11, 23)
SAVED_FILE_NAME = "2026-11-23-o-sol.png"
SUN_SHAPE: dict[str, object] = {
    "type": "circle",
    "x": 200,
    "y": 150,
    "radius": 40,
    "color": "yellow",
}
VALID_ARGUMENTS: dict[str, object] = {"discovery_title": "O Sol", "shapes": [SUN_SHAPE]}
SUN_DRAWING = Drawing(
    title="O Sol", shapes=(Circle(center=Point(200, 150), radius=40, color="yellow"),)
)


class InMemoryDrawingRepository:
    """Keeps the saved drawings in a list instead of the disk."""

    def __init__(self) -> None:
        self.saved: list[tuple[Drawing, date]] = []

    def save(self, drawing: Drawing, drawn_on: date) -> str:
        self.saved.append((drawing, drawn_on))
        return SAVED_FILE_NAME


class FullDiskDrawingRepository:
    def save(self, drawing: Drawing, drawn_on: date) -> str:
        raise DrawingStorageError("no space left on device")


def arguments_with(**changes: object) -> dict[str, object]:
    return {**VALID_ARGUMENTS, **changes}


@pytest.fixture
def repository() -> InMemoryDrawingRepository:
    return InMemoryDrawingRepository()


@pytest.fixture
def chalkboard() -> Chalkboard:
    return Chalkboard(capacity=1)


@pytest.fixture
def saved_discoveries() -> SavedDiscoveries:
    """Pretends save_discovery already stored 'O Sol' and 'A Lua' in this conversation."""
    discoveries = SavedDiscoveries()
    discoveries.remember("O Sol")
    discoveries.remember("A Lua")
    return discoveries


@pytest.fixture
def draw_tool(
    repository: InMemoryDrawingRepository,
    chalkboard: Chalkboard,
    saved_discoveries: SavedDiscoveries,
) -> DrawTool:
    return DrawTool(repository, chalkboard, saved_discoveries, today=lambda: TODAY)


def test_definition_is_named_draw(draw_tool: DrawTool) -> None:
    assert draw_tool.definition.name == "draw"


def test_saves_the_drawing_with_todays_date(
    draw_tool: DrawTool, repository: InMemoryDrawingRepository
) -> None:
    draw_tool.run(VALID_ARGUMENTS)

    assert repository.saved == [(SUN_DRAWING, TODAY)]


def test_pins_the_drawing_on_the_chalkboard(draw_tool: DrawTool, chalkboard: Chalkboard) -> None:
    draw_tool.run(VALID_ARGUMENTS)

    assert chalkboard.drawings == (SUN_DRAWING,)


def test_tells_the_model_the_file_name_and_the_chalkboard(draw_tool: DrawTool) -> None:
    assert draw_tool.run(VALID_ARGUMENTS) == (
        f"Drawn as {SAVED_FILE_NAME} and pinned on your chalkboard."
    )


def test_tells_the_model_which_drawing_was_erased(draw_tool: DrawTool) -> None:
    draw_tool.run(VALID_ARGUMENTS)

    result = draw_tool.run(arguments_with(discovery_title="A Lua"))

    assert result.endswith("To make room, you erased the old drawing 'O Sol'.")


def test_accepts_the_saved_file_name_and_draws_with_the_real_title(
    repository: InMemoryDrawingRepository, chalkboard: Chalkboard
) -> None:
    saved_discoveries = SavedDiscoveries()
    saved_discoveries.remember("O Sol", "2026-11-23-o-sol.md")
    tool = DrawTool(repository, chalkboard, saved_discoveries, today=lambda: TODAY)

    tool.run(arguments_with(discovery_title="2026-11-23-o-sol"))

    assert repository.saved == [(SUN_DRAWING, TODAY)]


def test_refuses_a_discovery_not_saved_in_this_conversation(draw_tool: DrawTool) -> None:
    with pytest.raises(ToolError, match="save it with save_discovery first"):
        draw_tool.run(arguments_with(discovery_title="Os Ursos"))


def test_refuses_a_second_drawing_of_the_same_discovery(draw_tool: DrawTool) -> None:
    draw_tool.run(VALID_ARGUMENTS)

    with pytest.raises(ToolError, match="already drew 'O Sol'"):
        draw_tool.run(VALID_ARGUMENTS)


def test_turns_a_broken_drawing_rule_into_a_tool_error(draw_tool: DrawTool) -> None:
    shape_outside_the_board = {**SUN_SHAPE, "x": 900}

    with pytest.raises(ToolError, match="invalid drawing: point"):
        draw_tool.run(arguments_with(shapes=[shape_outside_the_board]))


def test_refuses_a_drawing_without_shapes(draw_tool: DrawTool) -> None:
    with pytest.raises(ToolError, match="at least one shape"):
        draw_tool.run(arguments_with(shapes=[]))


def test_does_not_pin_an_invalid_drawing(draw_tool: DrawTool, chalkboard: Chalkboard) -> None:
    with pytest.raises(ToolError):
        draw_tool.run(arguments_with(shapes=[{"type": "triangle"}]))

    assert chalkboard.drawings == ()


def test_lets_the_model_retry_after_an_invalid_drawing(draw_tool: DrawTool) -> None:
    with pytest.raises(ToolError):
        draw_tool.run(arguments_with(shapes=[]))

    assert draw_tool.run(VALID_ARGUMENTS).startswith("Drawn as")


def test_rejects_a_missing_discovery_title(draw_tool: DrawTool) -> None:
    with pytest.raises(ToolError, match="discovery_title"):
        draw_tool.run({"shapes": [SUN_SHAPE]})


def test_turns_storage_failures_into_tool_errors(
    chalkboard: Chalkboard, saved_discoveries: SavedDiscoveries
) -> None:
    tool = DrawTool(FullDiskDrawingRepository(), chalkboard, saved_discoveries, today=lambda: TODAY)

    with pytest.raises(ToolError, match="no space left on device"):
        tool.run(VALID_ARGUMENTS)


class RecordingBody:
    def __init__(self) -> None:
        self.shown_chalkboards: list[tuple[Drawing, ...]] = []

    def go_to(self, place: Place) -> None:
        pass

    def show_chalkboard(self, drawings: tuple[Drawing, ...]) -> None:
        self.shown_chalkboards.append(drawings)


def test_shows_the_updated_chalkboard_on_the_body(
    repository: InMemoryDrawingRepository,
    chalkboard: Chalkboard,
    saved_discoveries: SavedDiscoveries,
) -> None:
    body = RecordingBody()
    tool = DrawTool(repository, chalkboard, saved_discoveries, today=lambda: TODAY, body=body)

    tool.run(VALID_ARGUMENTS)

    assert body.shown_chalkboards == [(SUN_DRAWING,)]


def test_does_not_show_the_chalkboard_when_the_drawing_is_invalid(
    repository: InMemoryDrawingRepository,
    chalkboard: Chalkboard,
    saved_discoveries: SavedDiscoveries,
) -> None:
    body = RecordingBody()
    tool = DrawTool(repository, chalkboard, saved_discoveries, today=lambda: TODAY, body=body)

    with pytest.raises(ToolError):
        tool.run(arguments_with(shapes=[]))

    assert body.shown_chalkboards == []
