from src.domain.drawing import Point, Stroke
from src.domain.tool import ToolError


def parse_strokes(raw_strokes: object) -> tuple[Stroke, ...]:
    """Turns the stroke list sent by the model into domain strokes, explaining any mistake.

    Each stroke is a list of [x, y] points, like [[200, 60], [250, 220]]. Coordinates may
    come as decimals (small models write 120.0), so they are rounded to whole pixels.
    """
    if not isinstance(raw_strokes, list):
        raise ToolError("the 'strokes' argument must be a list of strokes")
    return tuple(
        _parse_stroke(position, raw_stroke)
        for position, raw_stroke in enumerate(raw_strokes, start=1)
    )


def _parse_stroke(position: int, raw_stroke: object) -> Stroke:
    if not isinstance(raw_stroke, list):
        raise ToolError(f"stroke {position} must be a list of [x, y] points")
    return Stroke(points=tuple(_parse_point(position, raw_point) for raw_point in raw_stroke))


def _parse_point(position: int, raw_point: object) -> Point:
    if not isinstance(raw_point, list) or len(raw_point) != 2:
        raise ToolError(f"stroke {position} has a point that is not an [x, y] pair")
    x, y = raw_point
    return Point(_coordinate(position, x), _coordinate(position, y))


def _coordinate(position: int, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ToolError(f"stroke {position} has a point with a coordinate that is not a number")
    return round(value)
