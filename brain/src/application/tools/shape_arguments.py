from src.domain.drawing import Circle, Line, Point, Rectangle, Shape, Text
from src.domain.tool import ToolError

DEFAULT_CHALK_COLOR = "white"
SHAPE_TYPES = ("line", "circle", "rectangle", "text")


def parse_shapes(raw_shapes: object) -> tuple[Shape, ...]:
    """Turns the shape list sent by the model into domain shapes, explaining any mistake."""
    if not isinstance(raw_shapes, list):
        raise ToolError("the 'shapes' argument must be a list of shapes")
    return tuple(
        _parse_shape(position, raw_shape) for position, raw_shape in enumerate(raw_shapes, start=1)
    )


def _parse_shape(position: int, raw_shape: object) -> Shape:
    if not isinstance(raw_shape, dict):
        raise ToolError(f"shape {position} must be an object with a 'type'")
    fields = _ShapeFields(position, raw_shape)
    match raw_shape.get("type"):
        case "line":
            return Line(
                start=fields.point("x1", "y1"), end=fields.point("x2", "y2"), color=fields.color()
            )
        case "circle":
            return Circle(
                center=fields.point("x", "y"), radius=fields.number("radius"), color=fields.color()
            )
        case "rectangle":
            return _rectangle(fields)
        case "text":
            return Text(
                position=fields.point("x", "y"), content=fields.text("text"), color=fields.color()
            )
        case unknown_type:
            raise ToolError(
                f"shape {position} has unknown type '{unknown_type}', "
                f"use one of: {', '.join(SHAPE_TYPES)}"
            )


def _rectangle(fields: "_ShapeFields") -> Rectangle:
    """Accepts the two corners in any order: small models often swap them."""
    first_x, first_y = fields.number("x1"), fields.number("y1")
    second_x, second_y = fields.number("x2"), fields.number("y2")
    return Rectangle(
        top_left=Point(min(first_x, second_x), min(first_y, second_y)),
        bottom_right=Point(max(first_x, second_x), max(first_y, second_y)),
        color=fields.color(),
    )


class _ShapeFields:
    """Reads typed fields from one raw shape, naming the shape in every error."""

    def __init__(self, position: int, raw_shape: dict[object, object]) -> None:
        self._position = position
        self._raw_shape = raw_shape

    def number(self, name: str) -> int:
        value = self._raw_shape.get(name)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ToolError(f"shape {self._position} needs a number in '{name}'")
        return round(value)

    def point(self, x_name: str, y_name: str) -> Point:
        return Point(self.number(x_name), self.number(y_name))

    def text(self, name: str) -> str:
        value = self._raw_shape.get(name)
        if not isinstance(value, str):
            raise ToolError(f"shape {self._position} needs a text in '{name}'")
        return value

    def color(self) -> str:
        value = self._raw_shape.get("color", DEFAULT_CHALK_COLOR)
        if not isinstance(value, str):
            raise ToolError(f"shape {self._position} needs a chalk color name in 'color'")
        return value.strip().lower()
