"""JSON Schema for asking the model, in structured output, whether and what to draw.

Built from the chalkboard rules, so the board size, chalk colors and text length the model
is allowed to write are always the ones the domain accepts. Every field of a shape is
required: structured output guarantees the shape of the JSON, and fields left optional
were simply skipped in experiments (circles without a center).
"""

from collections.abc import Mapping

from src.domain.drawing import CANVAS_HEIGHT, CANVAS_WIDTH, CHALK_COLORS, MAX_TEXT_LENGTH

# Fewer than the domain allows (30): each shape costs ~25 written tokens, and a dozen
# simple chalk shapes are plenty for a little drawing.
MAX_SUGGESTED_SHAPES = 12
MAX_CIRCLE_RADIUS = CANVAS_HEIGHT // 2

_X_FIELD = {"type": "integer", "minimum": 0, "maximum": CANVAS_WIDTH}
_Y_FIELD = {"type": "integer", "minimum": 0, "maximum": CANVAS_HEIGHT}
_TWO_CORNERS = {"x1": _X_FIELD, "y1": _Y_FIELD, "x2": _X_FIELD, "y2": _Y_FIELD}


def _shape(type_name: str, fields: Mapping[str, object]) -> dict[str, object]:
    properties: dict[str, object] = {
        "type": {"const": type_name},
        **fields,
        "color": {"type": "string", "enum": list(CHALK_COLORS)},
    }
    return {"type": "object", "properties": properties, "required": list(properties)}


DRAWING_DECISION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "wants_to_draw": {"type": "boolean"},
        "shapes": {
            "type": "array",
            "maxItems": MAX_SUGGESTED_SHAPES,
            "items": {
                "anyOf": [
                    _shape("line", _TWO_CORNERS),
                    _shape(
                        "circle",
                        {
                            "x": _X_FIELD,
                            "y": _Y_FIELD,
                            "radius": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": MAX_CIRCLE_RADIUS,
                            },
                        },
                    ),
                    _shape("rectangle", _TWO_CORNERS),
                    _shape(
                        "text",
                        {
                            "x": _X_FIELD,
                            "y": _Y_FIELD,
                            "text": {"type": "string", "maxLength": MAX_TEXT_LENGTH},
                        },
                    ),
                ]
            },
        },
    },
    "required": ["wants_to_draw", "shapes"],
}
