from collections.abc import Sequence

import pytest

from src.domain.doodle import (
    Doodle,
    DoodleLibrary,
    InvalidDoodleError,
    UnknownCategoryError,
)
from src.domain.drawing import MAX_POINTS_PER_STROKE, Point

DIAGONAL = ((0, 0), (255, 255))


def first_doodle(doodles: Sequence[Doodle]) -> Doodle:
    return doodles[0]


@pytest.fixture
def cat() -> Doodle:
    return Doodle(category="cat", strokes=(DIAGONAL,))


@pytest.fixture
def library(cat: Doodle) -> DoodleLibrary:
    another_cat = Doodle(category="cat", strokes=(((10, 10), (20, 20)),))
    star = Doodle(category="star", strokes=(DIAGONAL,))
    return DoodleLibrary({"cat": [cat, another_cat], "star": [star]}, choose=first_doodle)


def test_fits_the_doodle_box_to_the_board_height_without_the_margins(cat: Doodle) -> None:
    """The 255x255 box becomes 240x240: the 300 px board minus a 30 px margin on each side."""
    (diagonal,) = cat.on_the_board()

    assert diagonal.points == (Point(80, 30), Point(320, 270))


def test_centers_a_doodle_drawn_in_the_top_of_its_box() -> None:
    """Quick, Draw! keeps wide doodles at the top; on the board they sit in the middle."""
    wide_doodle = Doodle(category="snake", strokes=(((0, 0), (255, 100)),))

    (stroke,) = wide_doodle.on_the_board()

    assert stroke.points == (Point(30, 83), Point(370, 217))


def test_centers_a_doodle_drawn_in_the_left_of_its_box() -> None:
    tall_doodle = Doodle(category="candle", strokes=(((0, 0), (51, 255)),))

    (stroke,) = tall_doodle.on_the_board()

    assert stroke.points == (Point(176, 30), Point(224, 270))


def test_keeps_every_stroke_of_the_doodle() -> None:
    doodle = Doodle(category="cross", strokes=(DIAGONAL, ((255, 0), (0, 255))))

    assert len(doodle.on_the_board()) == 2


def test_rejects_a_doodle_without_strokes() -> None:
    with pytest.raises(InvalidDoodleError):
        Doodle(category="nothing", strokes=())


def test_rejects_a_doodle_without_category() -> None:
    with pytest.raises(InvalidDoodleError):
        Doodle(category=" ", strokes=(DIAGONAL,))


def test_rejects_a_point_outside_the_doodle_box() -> None:
    with pytest.raises(InvalidDoodleError, match="outside its 255x255 box"):
        Doodle(category="cat", strokes=(((0, 0), (256, 10)),))


def test_rejects_a_stroke_with_too_many_points() -> None:
    with pytest.raises(InvalidDoodleError):
        Doodle(category="cat", strokes=(((10, 10),) * (MAX_POINTS_PER_STROKE + 1),))


def test_lists_the_categories_in_order(library: DoodleLibrary) -> None:
    assert library.categories == ("cat", "star")


def test_picks_one_doodle_of_the_category(library: DoodleLibrary, cat: Doodle) -> None:
    assert library.pick("cat") == cat


def test_picks_at_random_by_default(cat: Doodle) -> None:
    another_cat = Doodle(category="cat", strokes=(((10, 10), (20, 20)),))
    library = DoodleLibrary({"cat": [cat, another_cat]})

    picked = {library.pick("cat") for _ in range(50)}

    assert picked == {cat, another_cat}


def test_raises_for_a_category_without_doodles(library: DoodleLibrary) -> None:
    with pytest.raises(UnknownCategoryError, match="volcano"):
        library.pick("volcano")


def test_leaves_out_categories_with_no_doodles(cat: Doodle) -> None:
    library = DoodleLibrary({"cat": [cat], "empty": []})

    assert library.categories == ("cat",)


def test_rejects_an_empty_library() -> None:
    with pytest.raises(InvalidDoodleError):
        DoodleLibrary({})
