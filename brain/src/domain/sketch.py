from collections.abc import Iterable
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

SKETCH_BOX_SIZE = 100
"""Sketches are drawn inside a 100x100 box, then enlarged to fit the chalkboard."""
BOARD_MARGIN = 30
"""Empty space kept between the sketch and the top and bottom of the board, in pixels."""

SketchPoint = tuple[int, int]


class InvalidSketchError(Exception):
    """Raised when a sketch or the sketch book breaks a rule (empty, outside its box...)."""


class UnknownSketchError(Exception):
    """Raised when the capybara asks for a sketch that is not in her sketch book."""


@dataclass(frozen=True)
class Sketch:
    """A ready-made chalk sketch (a star, a cat...) the capybara knows how to draw.

    Like everything on her board, it is only strokes of the same chalk, never words.
    """

    name: str
    description: str
    """What the sketch can stand for, so she can match it to a discovery."""
    strokes: tuple[tuple[SketchPoint, ...], ...]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.description.strip():
            raise InvalidSketchError("a sketch needs a name and a description")
        if not 1 <= len(self.strokes) <= MAX_STROKES_PER_DRAWING:
            raise InvalidSketchError(
                f"sketch '{self.name}' needs 1 to {MAX_STROKES_PER_DRAWING} strokes"
            )
        for stroke in self.strokes:
            self._ensure_valid_stroke(stroke)

    def on_the_board(self) -> tuple[Stroke, ...]:
        """The sketch enlarged and centered on the chalkboard, ready to be drawn."""
        scale = (CANVAS_HEIGHT - 2 * BOARD_MARGIN) / SKETCH_BOX_SIZE
        left = (CANVAS_WIDTH - SKETCH_BOX_SIZE * scale) / 2
        top = float(BOARD_MARGIN)
        return tuple(
            Stroke(
                points=tuple(
                    Point(round(left + x * scale), round(top + y * scale)) for x, y in stroke
                )
            )
            for stroke in self.strokes
        )

    def _ensure_valid_stroke(self, stroke: tuple[SketchPoint, ...]) -> None:
        if not MIN_POINTS_PER_STROKE <= len(stroke) <= MAX_POINTS_PER_STROKE:
            raise InvalidSketchError(
                f"sketch '{self.name}' has a stroke with {len(stroke)} points, "
                f"use {MIN_POINTS_PER_STROKE} to {MAX_POINTS_PER_STROKE}"
            )
        for x, y in stroke:
            if not 0 <= x <= SKETCH_BOX_SIZE or not 0 <= y <= SKETCH_BOX_SIZE:
                raise InvalidSketchError(
                    f"sketch '{self.name}' has the point ({x}, {y}) outside its "
                    f"{SKETCH_BOX_SIZE}x{SKETCH_BOX_SIZE} box"
                )


class SketchBook:
    """Every sketch the capybara knows, found by name."""

    def __init__(self, sketches: Iterable[Sketch]) -> None:
        self._sketches: dict[str, Sketch] = {}
        for sketch in sketches:
            if sketch.name in self._sketches:
                raise InvalidSketchError(f"the sketch book has two sketches called '{sketch.name}'")
            self._sketches[sketch.name] = sketch
        if not self._sketches:
            raise InvalidSketchError("the sketch book needs at least one sketch")

    @property
    def sketches(self) -> tuple[Sketch, ...]:
        return tuple(self._sketches.values())

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._sketches)

    def find(self, name: str) -> Sketch:
        try:
            return self._sketches[name]
        except KeyError:
            raise UnknownSketchError(f"there is no sketch called '{name}'") from None
