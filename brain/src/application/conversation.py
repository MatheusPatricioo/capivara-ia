import logging
from collections.abc import Mapping, Sequence

from src.domain.language_model import ChatMessage, LanguageModel, Role, ToolCall
from src.domain.tool import Tool, ToolError

DEFAULT_MAX_STEPS = 5

logger = logging.getLogger(__name__)


class StepLimitReachedError(Exception):
    """Raised when the model keeps asking for tools beyond the allowed number of steps."""


class Conversation:
    def __init__(
        self,
        language_model: LanguageModel,
        system_prompt: str,
        tools: Sequence[Tool] = (),
        max_steps: int = DEFAULT_MAX_STEPS,
        tool_result_reminder: str = "",
        tool_result_reminders: Mapping[str, str] | None = None,
    ) -> None:
        """tool_result_reminder goes after every tool result, unless tool_result_reminders
        has an entry for that tool name: then that text is used instead ('' means none).
        """
        self._language_model = language_model
        self._history = [ChatMessage(role=Role.SYSTEM, content=system_prompt)]
        self._tools_by_name = {tool.definition.name: tool for tool in tools}
        self._max_steps = max_steps
        self._tool_result_reminder = tool_result_reminder
        self._tool_result_reminders = dict(tool_result_reminders or {})

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        return tuple(self._history)

    def send(self, user_message: str) -> str:
        turn_messages = [ChatMessage(role=Role.USER, content=user_message)]
        tool_definitions = [tool.definition for tool in self._tools_by_name.values()]
        for step in range(1, self._max_steps + 1):
            reply = self._language_model.chat([*self._history, *turn_messages], tool_definitions)
            turn_messages.append(reply)
            if not reply.tool_calls:
                self._history.extend(turn_messages)
                logger.info("Answered in %d step(s)", step)
                return reply.content
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
        tool = self._tools_by_name.get(tool_call.name)
        if tool is None:
            logger.warning("Unknown tool requested: %s", tool_call.name)
            tool_result = f"Error: unknown tool '{tool_call.name}'"
        else:
            try:
                tool_result = tool.run(tool_call.arguments)
            except ToolError as error:
                logger.warning("Tool %s failed: %s", tool_call.name, error)
                tool_result = f"Error: {error}"
        return ChatMessage(
            role=Role.TOOL,
            content=self._with_reminder(tool_result, tool_call.name),
            tool_name=tool_call.name,
        )

    def _with_reminder(self, tool_result: str, tool_name: str) -> str:
        """Puts the reminder right after the tool result, the last thing the model reads."""
        reminder = self._tool_result_reminders.get(tool_name, self._tool_result_reminder)
        if not reminder:
            return tool_result
        return f"{tool_result}\n\n{reminder}"
