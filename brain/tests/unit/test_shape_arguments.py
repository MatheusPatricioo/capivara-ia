import pytest

from src.application.tools.shape_arguments import parse_shapes
from src.domain.drawing import Circle, InvalidDrawingError, Line, Point, Rectangle, Text
from src.domain.tool import ToolError


def test_parses_a_line() -> None:
    shapes = parse_shapes(
        [{"type": "line", "x1": 0, "y1": 10, "x2": 50, "y2": 60, "color": "blue"}]
    )

    assert shapes == (Line(start=Point(0, 10), end=Point(50, 60), color="blue"),)


def test_parses_a_circle() -> None:
    shapes = parse_shapes([{"type": "circle", "x": 200, "y": 150, "radius": 40, "color": "yellow"}])

    assert shapes == (Circle(center=Point(200, 150), radius=40, color="yellow"),)


def test_parses_a_rectangle() -> None:
    shapes = parse_shapes([{"type": "rectangle", "x1": 10, "y1": 20, "x2": 30, "y2": 40}])

    assert shapes == (Rectangle(top_left=Point(10, 20), bottom_right=Point(30, 40), color="white"),)


def test_parses_a_text() -> None:
    shapes = parse_shapes([{"type": "text", "x": 5, "y": 5, "text": "capim", "color": "green"}])

    assert shapes == (Text(position=Point(5, 5), content="capim", color="green"),)


def test_uses_white_chalk_when_no_color_is_given() -> None:
    shapes = parse_shapes([{"type": "circle", "x": 200, "y": 150, "radius": 40}])

    assert shapes[0].color == "white"


def test_accepts_the_rectangle_corners_in_any_order() -> None:
    shapes = parse_shapes([{"type": "rectangle", "x1": 30, "y1": 40, "x2": 10, "y2": 20}])

    assert shapes == (Rectangle(top_left=Point(10, 20), bottom_right=Point(30, 40), color="white"),)


def test_rounds_decimal_coordinates() -> None:
    shapes = parse_shapes([{"type": "circle", "x": 199.6, "y": 150.2, "radius": 40}])

    assert shapes[0] == Circle(center=Point(200, 150), radius=40, color="white")


def test_normalizes_the_color_name() -> None:
    shapes = parse_shapes([{"type": "circle", "x": 200, "y": 150, "radius": 40, "color": " Pink "}])

    assert shapes[0].color == "pink"


def test_rejects_shapes_that_are_not_a_list() -> None:
    with pytest.raises(ToolError, match="list of shapes"):
        parse_shapes("a big sun")


def test_rejects_a_shape_that_is_not_an_object() -> None:
    with pytest.raises(ToolError, match="shape 1 must be an object"):
        parse_shapes(["circle"])


def test_rejects_an_unknown_shape_type() -> None:
    with pytest.raises(ToolError, match="shape 1 has unknown type 'triangle'"):
        parse_shapes([{"type": "triangle"}])


def test_names_the_shape_with_a_missing_number() -> None:
    valid_circle = {"type": "circle", "x": 200, "y": 150, "radius": 40}

    with pytest.raises(ToolError, match="shape 2 needs a number in 'radius'"):
        parse_shapes([valid_circle, {"type": "circle", "x": 200, "y": 150}])


def test_rejects_a_boolean_as_number() -> None:
    with pytest.raises(ToolError, match="'x'"):
        parse_shapes([{"type": "circle", "x": True, "y": 150, "radius": 40}])


def test_rejects_a_text_shape_without_text() -> None:
    with pytest.raises(ToolError, match="needs a text in 'text'"):
        parse_shapes([{"type": "text", "x": 5, "y": 5}])


def test_lets_domain_rules_reject_a_point_outside_the_board() -> None:
    with pytest.raises(InvalidDrawingError):
        parse_shapes([{"type": "circle", "x": 900, "y": 150, "radius": 40}])
