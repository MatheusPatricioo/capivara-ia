import logging
from collections.abc import Callable
from datetime import date

from src.application.tools.saved_discoveries import SavedDiscoveries
from src.application.tools.shape_arguments import SHAPE_TYPES, parse_shapes
from src.domain.body import Body
from src.domain.chalkboard import Chalkboard
from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    CHALK_COLORS,
    MAX_SHAPES_PER_DRAWING,
    Drawing,
    DrawingRepository,
    DrawingStorageError,
    InvalidDrawingError,
)
from src.domain.language_model import ToolDefinition
from src.domain.tool import ToolError

logger = logging.getLogger(__name__)

NUMBER_FIELD = {"type": "number"}


class DrawTool:
    def __init__(
        self,
        repository: DrawingRepository,
        chalkboard: Chalkboard,
        saved_discoveries: SavedDiscoveries,
        today: Callable[[], date] = date.today,
        body: Body | None = None,
    ) -> None:
        self._repository = repository
        self._chalkboard = chalkboard
        self._saved_discoveries = saved_discoveries
        self._today = today
        self._body = body

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="draw",
            description=(
                "Draws a discovery you saved in this conversation on your chalkboard, "
                "using simple chalk shapes. Each discovery can get only one drawing. "
                f"The board is {CANVAS_WIDTH} wide and {CANVAS_HEIGHT} tall: (0, 0) is the "
                "top-left corner and y grows downwards. "
                f"Use at most {MAX_SHAPES_PER_DRAWING} shapes. "
                "line: x1, y1, x2, y2. circle: x, y (center), radius. "
                "rectangle: x1, y1, x2, y2 (two corners). text: x, y, text (short)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "discovery_title": {
                        "type": "string",
                        "description": "The same title you used in save_discovery.",
                    },
                    "shapes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": list(SHAPE_TYPES)},
                                "x": NUMBER_FIELD,
                                "y": NUMBER_FIELD,
                                "x1": NUMBER_FIELD,
                                "y1": NUMBER_FIELD,
                                "x2": NUMBER_FIELD,
                                "y2": NUMBER_FIELD,
                                "radius": NUMBER_FIELD,
                                "text": {"type": "string"},
                                "color": {"type": "string", "enum": list(CHALK_COLORS)},
                            },
                            "required": ["type"],
                        },
                    },
                },
                "required": ["discovery_title", "shapes"],
            },
        )

    def run(self, arguments: dict[str, object]) -> str:
        title = self._saved_title(self._required_title(arguments))
        try:
            drawing = Drawing(title=title, shapes=parse_shapes(arguments.get("shapes")))
        except InvalidDrawingError as error:
            raise ToolError(f"invalid drawing: {error}") from error
        try:
            file_name = self._repository.save(drawing, self._today())
        except DrawingStorageError as error:
            raise ToolError(f"could not save the drawing: {error}") from error
        erased = self._chalkboard.pin(drawing)
        self._saved_discoveries.mark_drawn(title)
        if self._body is not None:
            self._body.show_chalkboard(self._chalkboard.drawings)
        logger.info("Drawing saved: %s (%d shape(s))", file_name, len(drawing.shapes))
        return self._result_message(file_name, erased)

    @staticmethod
    def _required_title(arguments: dict[str, object]) -> str:
        value = arguments.get("discovery_title")
        if not isinstance(value, str) or not value.strip():
            raise ToolError("the 'discovery_title' argument must be a non-empty text")
        return value.strip()

    def _saved_title(self, requested_name: str) -> str:
        """Finds the real title of a saved discovery that was not drawn yet."""
        title = self._saved_discoveries.title_for(requested_name)
        if title is None:
            raise ToolError(
                f"'{requested_name}' is not a discovery you saved in this conversation: "
                "save it with save_discovery first, then draw it using the same title"
            )
        if self._saved_discoveries.was_drawn(title):
            raise ToolError(f"you already drew '{title}': each discovery gets only one drawing")
        return title

    @staticmethod
    def _result_message(file_name: str, erased: Drawing | None) -> str:
        message = f"Drawn as {file_name} and pinned on your chalkboard."
        if erased is None:
            return message
        return f"{message} To make room, you erased the old drawing '{erased.title}'."
