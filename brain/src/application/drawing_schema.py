"""JSON Schema for asking the model, in structured output, whether and what to draw.

She does not invent coordinates (a small model cannot place points well): she only picks
one sketch from her sketch book by name, so the answer is short and always a real sketch.
"""

from collections.abc import Sequence


def drawing_decision_schema(sketch_names: Sequence[str]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "wants_to_draw": {"type": "boolean"},
            "sketch": {"type": "string", "enum": list(sketch_names)},
        },
        "required": ["wants_to_draw", "sketch"],
    }
