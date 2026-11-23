"""JSON Schema for asking the model, in structured output, whether and what to draw.

Built from the chalkboard rules, so the board size the model may draw on is always the one
the domain accepts. The capybara has a single brush, so a drawing is only a list of
strokes, each one a list of [x, y] points: there is no text, color or other shape to choose.
"""

from src.domain.drawing import CANVAS_HEIGHT, CANVAS_WIDTH, MIN_POINTS_PER_STROKE

# Fewer than the domain allows: every point costs written tokens (and seconds on a local
# model), and a few simple strokes are plenty for a little chalk sketch.
MAX_SUGGESTED_STROKES = 6
MAX_SUGGESTED_POINTS_PER_STROKE = 10

# [x, y] instead of {"x": ..., "y": ...}: the same point in about half the tokens.
_POINT: dict[str, object] = {
    "type": "array",
    "prefixItems": [
        {"type": "integer", "minimum": 0, "maximum": CANVAS_WIDTH},
        {"type": "integer", "minimum": 0, "maximum": CANVAS_HEIGHT},
    ],
    "minItems": 2,
    "maxItems": 2,
}

_STROKE: dict[str, object] = {
    "type": "array",
    "minItems": MIN_POINTS_PER_STROKE,
    "maxItems": MAX_SUGGESTED_POINTS_PER_STROKE,
    "items": _POINT,
}

DRAWING_DECISION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "wants_to_draw": {"type": "boolean"},
        "strokes": {"type": "array", "maxItems": MAX_SUGGESTED_STROKES, "items": _STROKE},
    },
    "required": ["wants_to_draw", "strokes"],
}
