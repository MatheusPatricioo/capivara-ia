from datetime import date

import pytest

from src.application.tools.recall_memory_tool import NOTHING_REMEMBERED_MESSAGE, RecallMemoryTool
from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemoryError, RememberedDiscovery
from src.domain.tool import ToolError

MIN_SIMILARITY = 0.5
FIREFLIES = Discovery(
    title="Vaga-lumes brilham",
    topic="insetos",
    summary="A luz vem de uma\nreação química.",
    sources=("https://example.com",),
    discovered_on=date(2026, 11, 24),
)


class ScriptedMemory:
    def __init__(self, remembered: list[RememberedDiscovery]) -> None:
        self._remembered = remembered

    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise AssertionError("the tool only recalls")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        return self._remembered[:limit]


class OfflineMemory:
    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise DiscoveryMemoryError("offline")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        raise DiscoveryMemoryError("offline")


@pytest.fixture
def tool() -> RecallMemoryTool:
    return RecallMemoryTool(
        ScriptedMemory([RememberedDiscovery(FIREFLIES, 0.8)]), MIN_SIMILARITY
    )


def test_returns_the_remembered_discovery_with_its_summary_in_one_line(
    tool: RecallMemoryTool,
) -> None:
    result = tool.run({"query": "luzinhas"})

    assert result == "1. Vaga-lumes brilham (tema: insetos)\nA luz vem de uma reação química."


def test_says_the_subject_is_new_when_nothing_is_close_enough() -> None:
    tool = RecallMemoryTool(ScriptedMemory([RememberedDiscovery(FIREFLIES, 0.2)]), MIN_SIMILARITY)

    assert tool.run({"query": "vulcões"}) == NOTHING_REMEMBERED_MESSAGE


def test_reports_an_offline_memory_to_the_model() -> None:
    tool = RecallMemoryTool(OfflineMemory(), MIN_SIMILARITY)

    with pytest.raises(ToolError, match="memory is not available"):
        tool.run({"query": "vaga-lumes"})


def test_rejects_a_blank_query(tool: RecallMemoryTool) -> None:
    with pytest.raises(ToolError, match="'query' must not be empty"):
        tool.run({"query": " "})
