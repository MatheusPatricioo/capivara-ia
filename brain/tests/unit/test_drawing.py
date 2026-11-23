import pytest

from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    MAX_POINTS_PER_STROKE,
    MAX_STROKES_PER_DRAWING,
    Drawing,
    InvalidDrawingError,
    Point,
    Stroke,
)


@pytest.fixture
def star() -> Stroke:
    """A five-pointed star drawn without lifting the chalk, ending where it began."""
    return Stroke(
        points=(
            Point(200, 60),
            Point(250, 220),
            Point(120, 120),
            Point(280, 120),
            Point(150, 220),
            Point(200, 60),
        )
    )


def test_accepts_a_point_on_the_board_corner() -> None:
    corner = Point(CANVAS_WIDTH, CANVAS_HEIGHT)

    assert corner == Point(CANVAS_WIDTH, CANVAS_HEIGHT)


def test_rejects_a_point_to_the_right_of_the_board() -> None:
    with pytest.raises(InvalidDrawingError):
        Point(CANVAS_WIDTH + 1, 0)


def test_rejects_a_point_with_negative_coordinate() -> None:
    with pytest.raises(InvalidDrawingError):
        Point(0, -1)


def test_accepts_a_stroke_with_two_points() -> None:
    line = Stroke(points=(Point(0, 0), Point(10, 10)))

    assert len(line.points) == 2


def test_rejects_a_stroke_with_a_single_point() -> None:
    with pytest.raises(InvalidDrawingError, match="a stroke needs"):
        Stroke(points=(Point(10, 10),))


def test_rejects_a_stroke_with_too_many_points() -> None:
    with pytest.raises(InvalidDrawingError, match="a stroke needs"):
        Stroke(points=(Point(10, 10),) * (MAX_POINTS_PER_STROKE + 1))


def test_creates_a_drawing_made_of_strokes(star: Stroke) -> None:
    drawing = Drawing(title="Constelações", strokes=(star,))

    assert drawing.strokes == (star,)


def test_rejects_a_drawing_without_strokes() -> None:
    with pytest.raises(InvalidDrawingError):
        Drawing(title="Nada", strokes=())


def test_rejects_a_drawing_with_too_many_strokes(star: Stroke) -> None:
    with pytest.raises(InvalidDrawingError):
        Drawing(title="Muitas estrelas", strokes=(star,) * (MAX_STROKES_PER_DRAWING + 1))


def test_rejects_a_drawing_without_title(star: Stroke) -> None:
    with pytest.raises(InvalidDrawingError):
        Drawing(title=" ", strokes=(star,))
