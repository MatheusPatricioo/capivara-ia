import pytest

from src.application.tools.feeling_tool import FeelingTool, always, search_feeling
from src.application.tools.web_search_tool import ALREADY_SEARCHED_MESSAGE, NO_RESULTS_MESSAGE
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.language_model import ToolDefinition
from src.domain.tool import ToolError
from tests.fakes.in_memory_emotional_memory import RecordingFeeler

FOUND_RESULT = "1. Capivaras\nhttps://example.com/capivaras\nComem plantas."
ARGUMENTS: dict[str, object] = {"query": "capivaras"}


class AnsweringTool:
    def __init__(self, answer: str) -> None:
        self._answer = answer

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="web_search", description="Searches.", parameters={})

    def run(self, arguments: dict[str, object]) -> str:
        return self._answer


class FailingTool(AnsweringTool):
    def run(self, arguments: dict[str, object]) -> str:
        raise ToolError("the search engine is down")


@pytest.fixture
def heart() -> RecordingFeeler:
    return RecordingFeeler()


def test_a_search_with_results_means_she_found_something() -> None:
    assert search_feeling(FOUND_RESULT) is EventKind.SEARCH_FOUND_SOMETHING


def test_a_search_without_results_means_she_found_nothing() -> None:
    assert search_feeling(NO_RESULTS_MESSAGE) is EventKind.SEARCH_FOUND_NOTHING


def test_a_search_she_already_did_means_repetition() -> None:
    result = ALREADY_SEARCHED_MESSAGE.format(query="capivaras", searched_on="2026-11-20")

    assert search_feeling(result) is EventKind.SEARCH_REPEATED


def test_she_feels_what_came_out_of_the_tool(heart: RecordingFeeler) -> None:
    tool = FeelingTool(AnsweringTool(FOUND_RESULT), heart, search_feeling)

    tool.run(ARGUMENTS)

    assert heart.felt == [EmotionalEvent(EventKind.SEARCH_FOUND_SOMETHING)]


def test_the_result_reaches_the_model_unchanged(heart: RecordingFeeler) -> None:
    tool = FeelingTool(AnsweringTool(FOUND_RESULT), heart, search_feeling)

    assert tool.run(ARGUMENTS) == FOUND_RESULT


def test_a_failing_tool_makes_her_feel_the_failure(heart: RecordingFeeler) -> None:
    tool = FeelingTool(FailingTool(""), heart, search_feeling, EventKind.SEARCH_FAILED)

    with pytest.raises(ToolError):
        tool.run(ARGUMENTS)

    assert heart.felt == [EmotionalEvent(EventKind.SEARCH_FAILED)]


def test_a_failure_with_nothing_to_feel_only_goes_back_to_the_model(
    heart: RecordingFeeler,
) -> None:
    tool = FeelingTool(FailingTool(""), heart, always(EventKind.DISCOVERY_SAVED))

    with pytest.raises(ToolError):
        tool.run(ARGUMENTS)

    assert heart.felt == []


def test_the_model_sees_the_same_tool(heart: RecordingFeeler) -> None:
    inner = AnsweringTool(FOUND_RESULT)

    assert FeelingTool(inner, heart, search_feeling).definition == inner.definition
