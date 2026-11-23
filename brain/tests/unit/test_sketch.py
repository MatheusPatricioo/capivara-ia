import pytest

from src.domain.drawing import MAX_POINTS_PER_STROKE, Point
from src.domain.sketch import (
    InvalidSketchError,
    Sketch,
    SketchBook,
    UnknownSketchError,
)

DIAGONAL = ((0, 0), (100, 100))


@pytest.fixture
def star() -> Sketch:
    return Sketch(name="estrela", description="estrela, constelações", strokes=(DIAGONAL,))


@pytest.fixture
def sketch_book(star: Sketch) -> SketchBook:
    moon = Sketch(name="lua", description="lua, noite", strokes=(DIAGONAL,))
    return SketchBook([star, moon])


def test_enlarges_the_box_to_the_board_height_without_the_margins(star: Sketch) -> None:
    """The 100x100 box becomes 240x240: the 300 px board minus a 30 px margin on each side."""
    (diagonal,) = star.on_the_board()

    assert diagonal.points == (Point(80, 30), Point(320, 270))


def test_keeps_the_strokes_in_order() -> None:
    sketch = Sketch(name="cruz", description="cruz", strokes=(((50, 0), (50, 100)), DIAGONAL))

    assert [stroke.points[0] for stroke in sketch.on_the_board()] == [Point(200, 30), Point(80, 30)]


def test_rejects_a_sketch_without_strokes() -> None:
    with pytest.raises(InvalidSketchError):
        Sketch(name="nada", description="nada", strokes=())


def test_rejects_a_sketch_without_description() -> None:
    with pytest.raises(InvalidSketchError):
        Sketch(name="estrela", description=" ", strokes=(DIAGONAL,))


def test_rejects_a_point_outside_the_sketch_box() -> None:
    with pytest.raises(InvalidSketchError, match="outside its 100x100 box"):
        Sketch(name="torto", description="torto", strokes=(((0, 0), (101, 50)),))


def test_rejects_a_stroke_with_a_single_point() -> None:
    with pytest.raises(InvalidSketchError):
        Sketch(name="ponto", description="ponto", strokes=(((10, 10),),))


def test_rejects_a_stroke_with_too_many_points() -> None:
    with pytest.raises(InvalidSketchError):
        Sketch(
            name="longo", description="longo", strokes=(((10, 10),) * (MAX_POINTS_PER_STROKE + 1),)
        )


def test_finds_a_sketch_by_name(sketch_book: SketchBook, star: Sketch) -> None:
    assert sketch_book.find("estrela") == star


def test_lists_the_sketch_names_in_order(sketch_book: SketchBook) -> None:
    assert sketch_book.names == ("estrela", "lua")


def test_raises_for_a_sketch_that_is_not_in_the_book(sketch_book: SketchBook) -> None:
    with pytest.raises(UnknownSketchError, match="dragão"):
        sketch_book.find("dragão")


def test_rejects_an_empty_sketch_book() -> None:
    with pytest.raises(InvalidSketchError):
        SketchBook([])


def test_rejects_two_sketches_with_the_same_name(star: Sketch) -> None:
    with pytest.raises(InvalidSketchError, match="two sketches called 'estrela'"):
        SketchBook([star, star])
