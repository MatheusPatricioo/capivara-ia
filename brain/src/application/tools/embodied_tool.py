from src.domain.body import Body, Place
from src.domain.language_model import ToolDefinition
from src.domain.tool import Tool


class EmbodiedTool:
    """Decorator that walks the body to a place before running the wrapped tool.

    The wrapped tool keeps its name and parameters, so the model sees no difference.
    """

    def __init__(self, tool: Tool, body: Body, place: Place) -> None:
        self._tool = tool
        self._body = body
        self._place = place

    @property
    def definition(self) -> ToolDefinition:
        return self._tool.definition

    def run(self, arguments: dict[str, object]) -> str:
        self._body.go_to(self._place)
        return self._tool.run(arguments)
