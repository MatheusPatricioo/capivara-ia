import logging
from collections.abc import Callable, Mapping, Sequence

from opentelemetry import trace
from opentelemetry.trace import Tracer

from src.application import tracing
from src.domain.language_model import ChatMessage, LanguageModel, Role, ToolCall
from src.domain.tool import Tool, ToolError

DEFAULT_MAX_STEPS = 5

logger = logging.getLogger(__name__)


class StepLimitReachedError(Exception):
    """Raised when the model keeps asking for tools beyond the allowed number of steps."""


def _go_on_at_once() -> None:
    pass


class Conversation:
    def __init__(
        self,
        language_model: LanguageModel,
        system_prompt: str,
        tools: Sequence[Tool] = (),
        max_steps: int = DEFAULT_MAX_STEPS,
        tool_result_reminder: str = "",
        tool_result_reminders: Mapping[str, str] | None = None,
        before_step: Callable[[], None] = _go_on_at_once,
        tracer: Tracer | None = None,
    ) -> None:
        """tool_result_reminder goes after every tool result, unless tool_result_reminders
        has an entry for that tool name: then that text is used instead ('' means none).
        before_step runs before each call to the model and may block, like her own
        thoughts waiting while her creator talks with her. A call already running is
        never cut in the middle.
        Each turn is traced as one span, with a child span for every tool it runs; the
        model calls nest there too when the model is traced (TracedLanguageModel).
        """
        self._language_model = language_model
        self._history = [ChatMessage(role=Role.SYSTEM, content=system_prompt)]
        self._tools_by_name = {tool.definition.name: tool for tool in tools}
        self._max_steps = max_steps
        self._tool_result_reminder = tool_result_reminder
        self._tool_result_reminders = dict(tool_result_reminders or {})
        self._before_step = before_step
        self._tracer = tracer or trace.get_tracer(__name__)

    @property
    def tool_names(self) -> set[str]:
        return set(self._tools_by_name)

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        return tuple(self._history)

    def send(self, user_message: str) -> str:
        """Raises StepLimitReachedError (and LanguageModelError from the model); the span
        of the turn then ends as an error with the exception attached."""
        with self._tracer.start_as_current_span("conversation_turn") as span:
            span.set_attribute(tracing.OBSERVATION_TYPE, tracing.AGENT)
            span.set_attribute(tracing.AGENT_NAME, tracing.CAPYBARA_AGENT_NAME)
            tracing.record_input(span, user_message)
            answer, step_count = self._answer(user_message)
            tracing.record_output(span, answer)
            tracing.record_metadata(span, "steps", step_count)
            return answer

    def _answer(self, user_message: str) -> tuple[str, int]:
        turn_messages = [ChatMessage(role=Role.USER, content=user_message)]
        tool_definitions = [tool.definition for tool in self._tools_by_name.values()]
        for step in range(1, self._max_steps + 1):
            self._before_step()
            reply = self._language_model.chat([*self._history, *turn_messages], tool_definitions)
            turn_messages.append(reply)
            if not reply.tool_calls:
                self._history.extend(turn_messages)
                logger.info("Answered in %d step(s)", step)
                return reply.content, step
            turn_messages.extend(self._run_tool(tool_call, step) for tool_call in reply.tool_calls)
        logger.warning("Step limit of %d reached without an answer", self._max_steps)
        raise StepLimitReachedError(f"The model did not answer within {self._max_steps} steps")

    def _run_tool(self, tool_call: ToolCall, step: int) -> ChatMessage:
        logger.info(
            "Tool call at step %d/%d: %s %s",
            step,
            self._max_steps,
            tool_call.name,
            tool_call.arguments,
        )
        with self._tracer.start_as_current_span(f"execute_tool {tool_call.name}") as span:
            span.set_attribute(tracing.OBSERVATION_TYPE, tracing.TOOL)
            span.set_attribute(tracing.OPERATION_NAME, "execute_tool")
            span.set_attribute(tracing.TOOL_NAME, tool_call.name)
            span.set_attribute(tracing.TOOL_ARGUMENTS, tracing.to_json(tool_call.arguments))
            tracing.record_metadata(span, "step", step)
            tool_result = self._tool_result(tool_call, span)
            span.set_attribute(tracing.TOOL_RESULT, tool_result)
        return ChatMessage(
            role=Role.TOOL,
            content=self._with_reminder(tool_result, tool_call.name),
            tool_name=tool_call.name,
        )

    def _tool_result(self, tool_call: ToolCall, span: trace.Span) -> str:
        """What goes back to the model. A failing tool does not stop the turn: the model
        reads the error and may correct itself, and the tool span shows it as an error."""
        tool = self._tools_by_name.get(tool_call.name)
        if tool is None:
            logger.warning("Unknown tool requested: %s", tool_call.name)
            tracing.mark_failed(span, "unknown tool")
            return f"Error: unknown tool '{tool_call.name}'"
        try:
            return tool.run(tool_call.arguments)
        except ToolError as error:
            logger.warning("Tool %s failed: %s", tool_call.name, error)
            tracing.mark_failed(span, str(error))
            return f"Error: {error}"

    def _with_reminder(self, tool_result: str, tool_name: str) -> str:
        """Puts the reminder right after the tool result, the last thing the model reads."""
        reminder = self._tool_result_reminders.get(tool_name, self._tool_result_reminder)
        if not reminder:
            return tool_result
        return f"{tool_result}\n\n{reminder}"
