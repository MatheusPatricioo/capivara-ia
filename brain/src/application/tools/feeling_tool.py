from collections.abc import Callable
from typing import Protocol

from src.application.tools.web_search_tool import ALREADY_SEARCHED_PREFIX, NO_RESULTS_MESSAGE
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.language_model import ToolDefinition
from src.domain.tool import Tool, ToolError


class Feeler(Protocol):
    """Anything that can feel an event (the Heart, or a fake in tests)."""

    def feel(self, event: EmotionalEvent) -> object: ...


def always(kind: EventKind) -> Callable[[str], EventKind | None]:
    """For tools whose success always means the same thing to her."""
    return lambda result: kind


def search_feeling(result: str) -> EventKind:
    """What a web search result means to her: found, found nothing or already knew it."""
    if result.startswith(NO_RESULTS_MESSAGE):
        return EventKind.SEARCH_FOUND_NOTHING
    if result.startswith(ALREADY_SEARCHED_PREFIX):
        return EventKind.SEARCH_REPEATED
    return EventKind.SEARCH_FOUND_SOMETHING


class FeelingTool:
    """Decorator: after the wrapped tool runs, she feels what came out of it.

    on_success turns the result into an event (or None for nothing to feel);
    on_failure is what she feels when the tool raises a ToolError. The error still goes
    back to the model as before. The model sees the same tool, name and parameters.
    """

    def __init__(
        self,
        tool: Tool,
        heart: Feeler,
        on_success: Callable[[str], EventKind | None],
        on_failure: EventKind | None = None,
    ) -> None:
        self._tool = tool
        self._heart = heart
        self._on_success = on_success
        self._on_failure = on_failure

    @property
    def definition(self) -> ToolDefinition:
        return self._tool.definition

    def run(self, arguments: dict[str, object]) -> str:
        try:
            tool_result = self._tool.run(arguments)
        except ToolError:
            if self._on_failure is not None:
                self._heart.feel(EmotionalEvent(self._on_failure))
            raise
        kind = self._on_success(tool_result)
        if kind is not None:
            self._heart.feel(EmotionalEvent(kind))
        return tool_result
