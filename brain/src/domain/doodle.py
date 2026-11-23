import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    MAX_POINTS_PER_STROKE,
    MAX_STROKES_PER_DRAWING,
    MIN_POINTS_PER_STROKE,
    Point,
    Stroke,
)

DOODLE_BOX_SIZE = 255
"""Doodles come drawn inside a 255x255 box (the Quick, Draw! format), then fit the board."""
BOARD_MARGIN = 30
"""Empty space kept between the doodle and the top and bottom of the board, in pixels."""

DoodlePoint = tuple[int, int]
DoodleStroke = tuple[DoodlePoint, ...]


class InvalidDoodleError(Exception):
    """Raised when a doodle or the doodle library breaks a rule (empty, outside its box...)."""


class UnknownCategoryError(Exception):
    """Raised when there are no doodles for the requested category."""


@dataclass(frozen=True)
class Doodle:
    """A quick hand-drawn sketch of one thing (a cat, a star...), made only of strokes.

    The strokes are kept as strokes, never turned into an image, so the world can draw
    them one by one on the chalkboard.
    """

    category: str
    strokes: tuple[DoodleStroke, ...]

    def __post_init__(self) -> None:
        if not self.category.strip():
            raise InvalidDoodleError("a doodle needs a category")
        if not 1 <= len(self.strokes) <= MAX_STROKES_PER_DRAWING:
            raise InvalidDoodleError(
                f"a '{self.category}' doodle needs 1 to {MAX_STROKES_PER_DRAWING} strokes"
            )
        for stroke in self.strokes:
            self._ensure_valid_stroke(stroke)

    def on_the_board(self) -> tuple[Stroke, ...]:
        """The doodle enlarged and centered on the chalkboard, ready to be drawn."""
        scale = (CANVAS_HEIGHT - 2 * BOARD_MARGIN) / DOODLE_BOX_SIZE
        left = (CANVAS_WIDTH - DOODLE_BOX_SIZE * scale) / 2
        top = float(BOARD_MARGIN)
        return tuple(
            Stroke(
                points=tuple(
                    Point(round(left + x * scale), round(top + y * scale)) for x, y in stroke
                )
            )
            for stroke in self.strokes
        )

    def _ensure_valid_stroke(self, stroke: DoodleStroke) -> None:
        if not MIN_POINTS_PER_STROKE <= len(stroke) <= MAX_POINTS_PER_STROKE:
            raise InvalidDoodleError(
                f"a '{self.category}' doodle has a stroke with {len(stroke)} points, "
                f"use {MIN_POINTS_PER_STROKE} to {MAX_POINTS_PER_STROKE}"
            )
        for x, y in stroke:
            if not 0 <= x <= DOODLE_BOX_SIZE or not 0 <= y <= DOODLE_BOX_SIZE:
                raise InvalidDoodleError(
                    f"a '{self.category}' doodle has the point ({x}, {y}) outside its "
                    f"{DOODLE_BOX_SIZE}x{DOODLE_BOX_SIZE} box"
                )


class DoodleLibrary:
    """Many doodles per category; each request picks one of them, so drawings vary."""

    def __init__(
        self,
        doodles_by_category: Mapping[str, Sequence[Doodle]],
        choose: Callable[[Sequence[Doodle]], Doodle] = random.choice,
    ) -> None:
        self._doodles_by_category = {
            category: tuple(doodles) for category, doodles in doodles_by_category.items() if doodles
        }
        if not self._doodles_by_category:
            raise InvalidDoodleError("the doodle library needs at least one doodle")
        self._choose = choose

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(self._doodles_by_category)

    def pick(self, category: str) -> Doodle:
        try:
            doodles = self._doodles_by_category[category]
        except KeyError:
            raise UnknownCategoryError(f"there are no doodles of '{category}'") from None
        return self._choose(doodles)
