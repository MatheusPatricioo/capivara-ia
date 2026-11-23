import logging
from datetime import date

import pytest

from src.application.chalkboard_artist import PinnedDrawing
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.seen_sources import SeenSources
from src.domain.discovery import Discovery, DiscoveryStorageError
from src.domain.drawing import Drawing, Point, Stroke
from src.domain.tool import ToolError

TODAY = date(2026, 11, 22)
SAVED_FILE_NAME = "2026-11-22-capivaras-nadam.md"
SAVE_DISCOVERY_TOOL_LOGGER = "src.application.tools.save_discovery_tool"
SEARCHED_URLS = ["https://example.com/swim", "http://example.com/pond"]
INVENTED_URL = "https://example.com/made-up"
VALID_ARGUMENTS: dict[str, object] = {
    "title": "  Capivaras nadam  ",
    "topic": "capivaras",
    "summary": "Eu sei prender a respiração por cinco minutos!",
    "sources": SEARCHED_URLS,
}


class InMemoryDiscoveryRepository:
    """Keeps the saved discoveries in a list instead of the disk."""

    def __init__(self) -> None:
        self.saved_discoveries: list[Discovery] = []

    def save(self, discovery: Discovery) -> str:
        self.saved_discoveries.append(discovery)
        return SAVED_FILE_NAME


class FullDiskDiscoveryRepository:
    def save(self, discovery: Discovery) -> str:
        raise DiscoveryStorageError("no space left on device")


def arguments_with(**changes: object) -> dict[str, object]:
    return {**VALID_ARGUMENTS, **changes}


@pytest.fixture
def repository() -> InMemoryDiscoveryRepository:
    return InMemoryDiscoveryRepository()


@pytest.fixture
def seen_sources() -> SeenSources:
    """Pretends web_search already showed the URLs used in VALID_ARGUMENTS."""
    sources = SeenSources()
    sources.remember(SEARCHED_URLS)
    return sources


@pytest.fixture
def save_discovery_tool(
    repository: InMemoryDiscoveryRepository, seen_sources: SeenSources
) -> SaveDiscoveryTool:
    return SaveDiscoveryTool(repository, seen_sources, today=lambda: TODAY)


def test_definition_is_named_save_discovery(save_discovery_tool: SaveDiscoveryTool) -> None:
    assert save_discovery_tool.definition.name == "save_discovery"


def test_definition_does_not_let_the_model_choose_a_file_name(
    save_discovery_tool: SaveDiscoveryTool,
) -> None:
    """Sources are optional: when she leaves them out, the latest search is cited."""
    assert save_discovery_tool.definition.parameters["required"] == ["title", "topic", "summary"]


def test_saves_the_discovery_with_todays_date(
    save_discovery_tool: SaveDiscoveryTool, repository: InMemoryDiscoveryRepository
) -> None:
    save_discovery_tool.run(VALID_ARGUMENTS)

    assert repository.saved_discoveries == [
        Discovery(
            title="Capivaras nadam",
            topic="capivaras",
            summary="Eu sei prender a respiração por cinco minutos!",
            sources=("https://example.com/swim", "http://example.com/pond"),
            discovered_on=TODAY,
        )
    ]


def test_tells_the_model_the_saved_file_name(save_discovery_tool: SaveDiscoveryTool) -> None:
    assert save_discovery_tool.run(VALID_ARGUMENTS).startswith(f"Saved as {SAVED_FILE_NAME}.")


def test_rejects_an_empty_source_list(save_discovery_tool: SaveDiscoveryTool) -> None:
    with pytest.raises(ToolError, match="at least one source"):
        save_discovery_tool.run(arguments_with(sources=[]))


def test_refuses_to_save_without_any_search_result_and_offers_to_give_up(
    repository: InMemoryDiscoveryRepository,
) -> None:
    tool = SaveDiscoveryTool(repository, SeenSources(), today=lambda: TODAY)

    with pytest.raises(ToolError, match="or do not save anything this time"):
        tool.run(VALID_ARGUMENTS)


def test_refuses_a_source_that_did_not_come_from_the_search(
    save_discovery_tool: SaveDiscoveryTool,
) -> None:
    with pytest.raises(ToolError, match=f"'{INVENTED_URL}' did not come from your web_search"):
        save_discovery_tool.run(arguments_with(sources=[*SEARCHED_URLS, INVENTED_URL]))


def test_saves_when_every_source_came_from_the_search(
    save_discovery_tool: SaveDiscoveryTool, repository: InMemoryDiscoveryRepository
) -> None:
    save_discovery_tool.run(arguments_with(sources=["https://example.com/swim"]))

    assert repository.saved_discoveries[0].sources == ("https://example.com/swim",)


def test_does_not_save_a_discovery_with_an_invented_source(
    save_discovery_tool: SaveDiscoveryTool, repository: InMemoryDiscoveryRepository
) -> None:
    with pytest.raises(ToolError):
        save_discovery_tool.run(arguments_with(sources=[INVENTED_URL]))

    assert repository.saved_discoveries == []


def test_logs_the_saved_file_and_its_sources(
    save_discovery_tool: SaveDiscoveryTool, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=SAVE_DISCOVERY_TOOL_LOGGER)

    save_discovery_tool.run(VALID_ARGUMENTS)

    assert caplog.messages == [
        f"Discovery saved: {SAVED_FILE_NAME} "
        "(sources: https://example.com/swim, http://example.com/pond)"
    ]


@pytest.mark.parametrize("field", ["title", "topic", "summary"])
def test_rejects_a_missing_text_field(save_discovery_tool: SaveDiscoveryTool, field: str) -> None:
    arguments = {name: value for name, value in VALID_ARGUMENTS.items() if name != field}

    with pytest.raises(ToolError, match=field):
        save_discovery_tool.run(arguments)


def test_rejects_a_blank_title(save_discovery_tool: SaveDiscoveryTool) -> None:
    with pytest.raises(ToolError, match="title"):
        save_discovery_tool.run(arguments_with(title="   "))


def test_cites_the_latest_search_when_she_leaves_the_sources_out(
    save_discovery_tool: SaveDiscoveryTool, repository: InMemoryDiscoveryRepository
) -> None:
    arguments = {name: value for name, value in VALID_ARGUMENTS.items() if name != "sources"}

    save_discovery_tool.run(arguments)

    assert repository.saved_discoveries[0].sources == tuple(SEARCHED_URLS)


def test_refuses_to_save_without_sources_and_without_any_search(
    repository: InMemoryDiscoveryRepository,
) -> None:
    tool = SaveDiscoveryTool(repository, SeenSources(), today=lambda: TODAY)
    arguments = {name: value for name, value in VALID_ARGUMENTS.items() if name != "sources"}

    with pytest.raises(ToolError, match="no web_search results"):
        tool.run(arguments)


def test_rejects_sources_that_are_not_a_list(save_discovery_tool: SaveDiscoveryTool) -> None:
    with pytest.raises(ToolError, match="sources"):
        save_discovery_tool.run(arguments_with(sources="https://example.com/swim"))


def test_rejects_a_source_that_is_not_a_web_url(save_discovery_tool: SaveDiscoveryTool) -> None:
    with pytest.raises(ToolError, match="invalid source URL"):
        save_discovery_tool.run(arguments_with(sources=["file:///C:/Windows/win.ini"]))


def test_rejects_a_source_that_is_not_text(save_discovery_tool: SaveDiscoveryTool) -> None:
    with pytest.raises(ToolError, match="invalid source URL"):
        save_discovery_tool.run(arguments_with(sources=[42]))


def test_does_not_save_when_the_arguments_are_invalid(
    save_discovery_tool: SaveDiscoveryTool, repository: InMemoryDiscoveryRepository
) -> None:
    with pytest.raises(ToolError):
        save_discovery_tool.run(arguments_with(sources=["not a url"]))

    assert repository.saved_discoveries == []


def test_turns_storage_failures_into_tool_errors(seen_sources: SeenSources) -> None:
    tool = SaveDiscoveryTool(FullDiskDiscoveryRepository(), seen_sources, today=lambda: TODAY)

    with pytest.raises(ToolError, match="no space left on device"):
        tool.run(VALID_ARGUMENTS)


DRAWING_FILE_NAME = "2026-11-22-capivaras-nadam.png"
SWIMMING_DRAWING = Drawing(
    title="Capivaras nadam",
    strokes=(
        Stroke(points=(Point(100, 200), Point(200, 180), Point(300, 200))),
        Stroke(points=(Point(180, 150), Point(220, 150))),
    ),
)
OLD_DRAWING = Drawing(title="O Sol", strokes=(Stroke(points=(Point(100, 100), Point(130, 130))),))


class RecordingIllustrator:
    """Answers every discovery with the same pinned drawing (or None) and records them."""

    def __init__(self, pinned_drawing: PinnedDrawing | None) -> None:
        self._pinned_drawing = pinned_drawing
        self.offered_discoveries: list[Discovery] = []

    def illustrate(self, discovery: Discovery) -> PinnedDrawing | None:
        self.offered_discoveries.append(discovery)
        return self._pinned_drawing


def tool_illustrated_by(
    illustrator: RecordingIllustrator,
    repository: InMemoryDiscoveryRepository,
    seen_sources: SeenSources,
) -> SaveDiscoveryTool:
    return SaveDiscoveryTool(
        repository, seen_sources, today=lambda: TODAY, illustrate=illustrator.illustrate
    )


@pytest.fixture
def illustrator_that_draws() -> RecordingIllustrator:
    return RecordingIllustrator(
        PinnedDrawing(drawing=SWIMMING_DRAWING, file_name=DRAWING_FILE_NAME, erased=None)
    )


def test_offers_the_saved_discovery_for_a_drawing(
    illustrator_that_draws: RecordingIllustrator,
    repository: InMemoryDiscoveryRepository,
    seen_sources: SeenSources,
) -> None:
    tool_illustrated_by(illustrator_that_draws, repository, seen_sources).run(VALID_ARGUMENTS)

    assert illustrator_that_draws.offered_discoveries == repository.saved_discoveries


def test_tells_her_what_she_already_drew(
    illustrator_that_draws: RecordingIllustrator,
    repository: InMemoryDiscoveryRepository,
    seen_sources: SeenSources,
) -> None:
    tool = tool_illustrated_by(illustrator_that_draws, repository, seen_sources)

    assert tool.run(VALID_ARGUMENTS) == (
        f"Saved as {SAVED_FILE_NAME}. Then you walked to your chalkboard and drew it with "
        f"2 chalk stroke(s), saved as {DRAWING_FILE_NAME}."
    )


def test_tells_her_which_old_drawing_was_erased(
    repository: InMemoryDiscoveryRepository, seen_sources: SeenSources
) -> None:
    illustrator = RecordingIllustrator(
        PinnedDrawing(drawing=SWIMMING_DRAWING, file_name=DRAWING_FILE_NAME, erased=OLD_DRAWING)
    )

    result = tool_illustrated_by(illustrator, repository, seen_sources).run(VALID_ARGUMENTS)

    assert result.endswith("To make room, you erased the old drawing 'O Sol'.")


def test_tells_her_when_the_discovery_did_not_become_a_drawing(
    repository: InMemoryDiscoveryRepository, seen_sources: SeenSources
) -> None:
    tool = tool_illustrated_by(RecordingIllustrator(None), repository, seen_sources)

    assert tool.run(VALID_ARGUMENTS) == (
        f"Saved as {SAVED_FILE_NAME}. At your chalkboard, this one did not become a drawing."
    )


def test_offers_no_drawing_when_the_discovery_was_not_saved(
    illustrator_that_draws: RecordingIllustrator,
    repository: InMemoryDiscoveryRepository,
    seen_sources: SeenSources,
) -> None:
    tool = tool_illustrated_by(illustrator_that_draws, repository, seen_sources)

    with pytest.raises(ToolError):
        tool.run(arguments_with(sources=[INVENTED_URL]))

    assert illustrator_that_draws.offered_discoveries == []
