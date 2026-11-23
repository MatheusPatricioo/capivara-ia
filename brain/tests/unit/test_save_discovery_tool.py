import logging
from datetime import date

import pytest

from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.saved_discoveries import SavedDiscoveries
from src.application.tools.seen_sources import SeenSources
from src.domain.discovery import Discovery, DiscoveryStorageError
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
    assert save_discovery_tool.definition.parameters["required"] == [
        "title",
        "topic",
        "summary",
        "sources",
    ]


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


def test_invites_the_drawing_with_the_exact_saved_title(
    save_discovery_tool: SaveDiscoveryTool,
) -> None:
    result = save_discovery_tool.run(VALID_ARGUMENTS)

    assert "call draw now with discovery_title 'Capivaras nadam'" in result


def test_rejects_an_empty_source_list(save_discovery_tool: SaveDiscoveryTool) -> None:
    with pytest.raises(ToolError, match="at least one source"):
        save_discovery_tool.run(arguments_with(sources=[]))


def test_refuses_to_save_before_any_web_search(repository: InMemoryDiscoveryRepository) -> None:
    tool = SaveDiscoveryTool(repository, SeenSources(), today=lambda: TODAY)

    with pytest.raises(ToolError, match="use web_search first"):
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


def test_remembers_the_saved_title_so_it_can_be_drawn(
    repository: InMemoryDiscoveryRepository, seen_sources: SeenSources
) -> None:
    saved_discoveries = SavedDiscoveries()
    tool = SaveDiscoveryTool(
        repository, seen_sources, today=lambda: TODAY, saved_discoveries=saved_discoveries
    )

    tool.run(VALID_ARGUMENTS)

    assert saved_discoveries.contains("Capivaras nadam")


def test_remembers_the_saved_file_name_as_another_way_to_find_it(
    repository: InMemoryDiscoveryRepository, seen_sources: SeenSources
) -> None:
    saved_discoveries = SavedDiscoveries()
    tool = SaveDiscoveryTool(
        repository, seen_sources, today=lambda: TODAY, saved_discoveries=saved_discoveries
    )

    tool.run(VALID_ARGUMENTS)

    assert saved_discoveries.title_for(SAVED_FILE_NAME) == "Capivaras nadam"


def test_turns_storage_failures_into_tool_errors(seen_sources: SeenSources) -> None:
    tool = SaveDiscoveryTool(FullDiskDiscoveryRepository(), seen_sources, today=lambda: TODAY)

    with pytest.raises(ToolError, match="no space left on device"):
        tool.run(VALID_ARGUMENTS)
