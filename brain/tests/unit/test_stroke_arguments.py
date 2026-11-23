import pytest

from src.application.tools.stroke_arguments import parse_strokes
from src.domain.drawing import InvalidDrawingError, Point, Stroke
from src.domain.tool import ToolError


def test_parses_a_stroke_through_its_points_in_order() -> None:
    strokes = parse_strokes([[[0, 10], [50, 60]]])

    assert strokes == (Stroke(points=(Point(0, 10), Point(50, 60))),)


def test_parses_several_strokes() -> None:
    strokes = parse_strokes([[[0, 0], [10, 10]], [[20, 20], [30, 30]]])

    assert len(strokes) == 2


def test_rounds_coordinates_written_as_decimals() -> None:
    strokes = parse_strokes([[[199.6, 150.2], [10, 10]]])

    assert strokes[0].points[0] == Point(200, 150)


def test_rejects_strokes_that_are_not_a_list() -> None:
    with pytest.raises(ToolError, match="must be a list of strokes"):
        parse_strokes("a big star")


def test_rejects_a_stroke_that_is_not_a_list_of_points() -> None:
    with pytest.raises(ToolError, match="stroke 1 must be a list of"):
        parse_strokes([{"type": "text", "text": "Estrelas"}])


def test_names_the_stroke_with_a_point_that_is_not_a_pair() -> None:
    valid_stroke = [[0, 0], [10, 10]]

    with pytest.raises(ToolError, match="stroke 2 has a point that is not an"):
        parse_strokes([valid_stroke, [[0, 0, 0], [10, 10]]])


def test_rejects_a_coordinate_written_as_text() -> None:
    with pytest.raises(ToolError, match="not a number"):
        parse_strokes([[["10", 0], [10, 10]]])


def test_rejects_a_boolean_coordinate() -> None:
    with pytest.raises(ToolError):
        parse_strokes([[[True, 0], [10, 10]]])


def test_rejects_a_point_outside_the_board() -> None:
    with pytest.raises(InvalidDrawingError):
        parse_strokes([[[900, 0], [10, 10]]])
