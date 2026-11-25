"""Records what happened in one eval run: every model reply and every tool call."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from src.domain.language_model import ChatMessage, LanguageModel, ToolDefinition
from src.domain.tool import Tool, ToolError


@dataclass(frozen=True)
class ToolCallRecord:
    name: str
    arguments: dict[str, object]
    result: str
    """What the tool returned, or the error message when it refused."""
    failed: bool


@dataclass
class RunTrace:
    """Filled while the conversation runs; read by the checks afterwards."""

    model_replies: int = 0
    tokens: int = 0
    tool_calls: list[ToolCallRecord] = field(default_factory=list)

    def calls_to(self, tool_name: str) -> list[ToolCallRecord]:
        return [call for call in self.tool_calls if call.name == tool_name]


class RecordingLanguageModel:
    """Decorator that counts replies and tokens into a trace."""

    def __init__(self, language_model: LanguageModel, trace: RunTrace) -> None:
        self._language_model = language_model
        self._trace = trace

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        reply = self._language_model.chat(messages, tools)
        self._trace.model_replies += 1
        self._trace.tokens += reply.token_count
        return reply


class RecordingTool:
    """Decorator that writes every call of a tool into a trace, refusals included."""

    def __init__(self, tool: Tool, trace: RunTrace) -> None:
        self._tool = tool
        self._trace = trace

    @property
    def definition(self) -> ToolDefinition:
        return self._tool.definition

    def run(self, arguments: dict[str, object]) -> str:
        try:
            result = self._tool.run(arguments)
        except ToolError as error:
            self._record(arguments, str(error), failed=True)
            raise
        self._record(arguments, result, failed=False)
        return result

    def _record(self, arguments: dict[str, object], result: str, failed: bool) -> None:
        self._trace.tool_calls.append(
            ToolCallRecord(self.definition.name, dict(arguments), result, failed)
        )
