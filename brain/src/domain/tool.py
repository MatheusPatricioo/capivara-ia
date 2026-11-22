from typing import Protocol

from src.domain.language_model import ToolDefinition


class ToolError(Exception):
    """Raised by a tool when it cannot do its job; the message goes back to the model."""


class Tool(Protocol):
    @property
    def definition(self) -> ToolDefinition: ...

    def run(self, arguments: dict[str, object]) -> str: ...
