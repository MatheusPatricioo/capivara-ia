import json

import pytest
from pydantic import ValidationError

from src.domain.drawing import Circle, Drawing, Line, Point, Rectangle, Text
from src.infrastructure.world_messages import GoToMessage, chalkboard_message

SUN_DRAWING = Drawing(
    title="O sol",
    shapes=(
        Line(start=Point(0, 250), end=Point(400, 250), color="green"),
        Circle(center=Point(200, 150), radius=40, color="yellow"),
        Rectangle(top_left=Point(10, 10), bottom_right=Point(60, 60), color="blue"),
        Text(position=Point(300, 20), content="sol", color="white"),
    ),
)


def test_go_to_message_has_the_type_and_the_point() -> None:
    message = GoToMessage(point="computer")

    assert json.loads(message.model_dump_json()) == {"type": "go_to", "point": "computer"}


def test_rejects_a_go_to_message_without_point() -> None:
    with pytest.raises(ValidationError):
        GoToMessage(point="")


def test_chalkboard_message_lists_every_shape_with_flat_fields() -> None:
    message = chalkboard_message((SUN_DRAWING,))

    assert json.loads(message.model_dump_json()) == {
        "type": "chalkboard",
        "drawings": [
            {
                "title": "O sol",
                "shapes": [
                    {"type": "line", "x1": 0, "y1": 250, "x2": 400, "y2": 250, "color": "green"},
                    {"type": "circle", "x": 200, "y": 150, "radius": 40, "color": "yellow"},
                    {"type": "rectangle", "x1": 10, "y1": 10, "x2": 60, "y2": 60, "color": "blue"},
                    {"type": "text", "x": 300, "y": 20, "text": "sol", "color": "white"},
                ],
            }
        ],
    }


def test_empty_chalkboard_message_has_no_drawings() -> None:
    assert chalkboard_message(()).drawings == []
