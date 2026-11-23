import random

import pytest

from src.domain.capybara_hand import STILL_HAND, CapybaraHand
from src.domain.doodle import DOODLE_BOX_SIZE, Doodle
from src.domain.drawing import MAX_POINTS_PER_STROKE

HOUSE = Doodle(
    category="house",
    strokes=(
        ((20, 120), (20, 250), (230, 250), (230, 120)),
        ((10, 130), (125, 10), (240, 130)),
    ),
)
LONG_LINE = Doodle(category="line", strokes=(((0, 0), (255, 0)),))


def hand_with_seed(seed: int) -> CapybaraHand:
    return CapybaraHand(rng=random.Random(seed))


@pytest.fixture
def redrawn_house() -> Doodle:
    return hand_with_seed(1).redraw(HOUSE)


def test_keeps_the_category(redrawn_house: Doodle) -> None:
    assert redrawn_house.category == "house"


def test_keeps_every_stroke_of_the_reference(redrawn_house: Doodle) -> None:
    assert len(redrawn_house.strokes) == len(HOUSE.strokes)


def test_never_copies_the_reference_exactly(redrawn_house: Doodle) -> None:
    assert redrawn_house != HOUSE


def test_two_drawings_of_the_same_reference_come_out_different() -> None:
    assert hand_with_seed(1).redraw(HOUSE) != hand_with_seed(2).redraw(HOUSE)


def test_the_same_seed_draws_the_same_way() -> None:
    """Randomness with a fixed seed is repeatable, which is what makes the hand testable."""
    assert hand_with_seed(7).redraw(HOUSE) == hand_with_seed(7).redraw(HOUSE)


def test_splits_long_lines_so_they_can_bend() -> None:
    (stroke,) = hand_with_seed(1).redraw(LONG_LINE).strokes

    assert len(stroke) > 2


def test_never_uses_more_points_than_a_stroke_allows() -> None:
    zigzag = tuple(
        (0 if index % 2 == 0 else 255, index * 6) for index in range(MAX_POINTS_PER_STROKE)
    )
    reference = Doodle(category="zigzag", strokes=(zigzag,))

    (stroke,) = hand_with_seed(1).redraw(reference).strokes

    assert len(stroke) <= MAX_POINTS_PER_STROKE


def test_keeps_every_point_inside_the_doodle_box(redrawn_house: Doodle) -> None:
    coordinates = [value for stroke in redrawn_house.strokes for point in stroke for value in point]

    assert 0 <= min(coordinates) and max(coordinates) <= DOODLE_BOX_SIZE


def test_a_still_hand_copies_the_reference() -> None:
    assert CapybaraHand(STILL_HAND, random.Random(1)).redraw(HOUSE) == Doodle(
        category="house",
        strokes=(
            ((10, 110), (10, 240), (220, 240), (220, 110)),
            ((0, 120), (115, 0), (230, 120)),
        ),
    )
