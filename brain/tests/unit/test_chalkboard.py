import pytest

from src.domain.chalkboard import Chalkboard
from src.domain.drawing import Circle, Drawing, InvalidDrawingError, Point

CAPACITY = 3


def make_drawing(title: str) -> Drawing:
    return Drawing(
        title=title,
        shapes=(Circle(center=Point(200, 150), radius=40, color="yellow"),),
    )


@pytest.fixture
def chalkboard() -> Chalkboard:
    return Chalkboard(capacity=CAPACITY)


@pytest.fixture
def full_chalkboard(chalkboard: Chalkboard) -> Chalkboard:
    for title in ("primeiro", "segundo", "terceiro"):
        chalkboard.pin(make_drawing(title))
    return chalkboard


def titles(chalkboard: Chalkboard) -> list[str]:
    return [drawing.title for drawing in chalkboard.drawings]


def test_starts_empty(chalkboard: Chalkboard) -> None:
    assert chalkboard.drawings == ()


def test_keeps_drawings_from_oldest_to_newest(full_chalkboard: Chalkboard) -> None:
    assert titles(full_chalkboard) == ["primeiro", "segundo", "terceiro"]


def test_pinning_on_a_board_with_room_erases_nothing(chalkboard: Chalkboard) -> None:
    erased = chalkboard.pin(make_drawing("primeiro"))

    assert erased is None


def test_pinning_on_a_full_board_erases_the_oldest_drawing(full_chalkboard: Chalkboard) -> None:
    full_chalkboard.pin(make_drawing("quarto"))

    assert titles(full_chalkboard) == ["segundo", "terceiro", "quarto"]


def test_pinning_on_a_full_board_returns_the_erased_drawing(full_chalkboard: Chalkboard) -> None:
    erased = full_chalkboard.pin(make_drawing("quarto"))

    assert erased == make_drawing("primeiro")


def test_rejects_a_capacity_of_zero() -> None:
    with pytest.raises(InvalidDrawingError):
        Chalkboard(capacity=0)
