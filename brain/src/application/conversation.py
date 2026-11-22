from collections.abc import Sequence

from src.domain.language_model import ChatMessage, LanguageModel, Role, ToolCall
from src.domain.tool import Tool, ToolError

DEFAULT_MAX_STEPS = 5


class StepLimitReachedError(Exception):
    """Raised when the model keeps asking for tools beyond the allowed number of steps."""


class Conversation:
    def __init__(
        self,
        language_model: LanguageModel,
        system_prompt: str,
        tools: Sequence[Tool] = (),
        max_steps: int = DEFAULT_MAX_STEPS,
    ) -> None:
        self._language_model = language_model
        self._history = [ChatMessage(role=Role.SYSTEM, content=system_prompt)]
        self._tools_by_name = {tool.definition.name: tool for tool in tools}
        self._max_steps = max_steps

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        return tuple(self._history)

    def send(self, user_message: str) -> str:
        turn_messages = [ChatMessage(role=Role.USER, content=user_message)]
        tool_definitions = [tool.definition for tool in self._tools_by_name.values()]
        for _ in range(self._max_steps):
            reply = self._language_model.chat([*self._history, *turn_messages], tool_definitions)
            turn_messages.append(reply)
            if not reply.tool_calls:
                self._history.extend(turn_messages)
                return reply.content
            turn_messages.extend(self._run_tool(tool_call) for tool_call in reply.tool_calls)
        raise StepLimitReachedError(f"The model did not answer within {self._max_steps} steps")

    def _run_tool(self, tool_call: ToolCall) -> ChatMessage:
        tool = self._tools_by_name.get(tool_call.name)
        if tool is None:
            result = f"Error: unknown tool '{tool_call.name}'"
        else:
            try:
                result = tool.run(tool_call.arguments)
            except ToolError as error:
                result = f"Error: {error}"
        return ChatMessage(role=Role.TOOL, content=result, tool_name=tool_call.name)
