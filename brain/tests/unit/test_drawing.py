import pytest

from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    MAX_SHAPES_PER_DRAWING,
    MAX_TEXT_LENGTH,
    Circle,
    Drawing,
    InvalidDrawingError,
    Line,
    Point,
    Rectangle,
    Text,
)


@pytest.fixture
def center() -> Point:
    return Point(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2)


@pytest.fixture
def sun(center: Point) -> Circle:
    return Circle(center=center, radius=40, color="yellow")


def test_accepts_a_point_on_the_board_corner() -> None:
    corner = Point(CANVAS_WIDTH, CANVAS_HEIGHT)

    assert corner == Point(CANVAS_WIDTH, CANVAS_HEIGHT)


def test_rejects_a_point_to_the_right_of_the_board() -> None:
    with pytest.raises(InvalidDrawingError):
        Point(CANVAS_WIDTH + 1, 0)


def test_rejects_a_point_with_negative_coordinate() -> None:
    with pytest.raises(InvalidDrawingError):
        Point(0, -1)


def test_rejects_an_unknown_chalk_color(center: Point) -> None:
    with pytest.raises(InvalidDrawingError, match="unknown chalk color"):
        Line(start=Point(0, 0), end=center, color="purple")


def test_rejects_a_circle_with_zero_radius(center: Point) -> None:
    with pytest.raises(InvalidDrawingError):
        Circle(center=center, radius=0, color="white")


def test_rejects_a_rectangle_with_corners_swapped() -> None:
    with pytest.raises(InvalidDrawingError):
        Rectangle(top_left=Point(100, 100), bottom_right=Point(10, 10), color="white")


def test_rejects_an_empty_text(center: Point) -> None:
    with pytest.raises(InvalidDrawingError):
        Text(position=center, content="   ", color="white")


def test_rejects_a_text_longer_than_the_limit(center: Point) -> None:
    with pytest.raises(InvalidDrawingError):
        Text(position=center, content="a" * (MAX_TEXT_LENGTH + 1), color="white")


def test_creates_a_drawing_with_different_shapes(sun: Circle, center: Point) -> None:
    label = Text(position=Point(10, 10), content="sol", color="white")

    drawing = Drawing(title="O sol", shapes=(sun, label))

    assert drawing.shapes == (sun, label)


def test_rejects_a_drawing_without_shapes() -> None:
    with pytest.raises(InvalidDrawingError):
        Drawing(title="Nada", shapes=())


def test_rejects_a_drawing_with_too_many_shapes(sun: Circle) -> None:
    with pytest.raises(InvalidDrawingError):
        Drawing(title="Muitos sóis", shapes=(sun,) * (MAX_SHAPES_PER_DRAWING + 1))


def test_rejects_a_drawing_without_title(sun: Circle) -> None:
    with pytest.raises(InvalidDrawingError):
        Drawing(title=" ", shapes=(sun,))
