from dataclasses import dataclass
from datetime import date
from typing import Protocol

CANVAS_WIDTH = 400
CANVAS_HEIGHT = 300
MAX_STROKES_PER_DRAWING = 20
MIN_POINTS_PER_STROKE = 2
MAX_POINTS_PER_STROKE = 40


class InvalidDrawingError(Exception):
    """Raised when a drawing breaks a chalkboard rule (out of the board, empty stroke...)."""


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def __post_init__(self) -> None:
        if not 0 <= self.x <= CANVAS_WIDTH or not 0 <= self.y <= CANVAS_HEIGHT:
            raise InvalidDrawingError(
                f"point ({self.x}, {self.y}) is outside the {CANVAS_WIDTH}x{CANVAS_HEIGHT} board"
            )


@dataclass(frozen=True)
class Stroke:
    """One line drawn with the chalk without lifting it, through its points in order.

    The capybara has a single brush: every drawing is only strokes of the same chalk,
    never words. A closed shape (a star, a round head) is a stroke that ends where it began.
    """

    points: tuple[Point, ...]

    def __post_init__(self) -> None:
        if not MIN_POINTS_PER_STROKE <= len(self.points) <= MAX_POINTS_PER_STROKE:
            raise InvalidDrawingError(
                f"a stroke needs {MIN_POINTS_PER_STROKE} to {MAX_POINTS_PER_STROKE} points, "
                f"got {len(self.points)}"
            )


@dataclass(frozen=True)
class Drawing:
    title: str
    strokes: tuple[Stroke, ...]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise InvalidDrawingError("drawing title must not be empty")
        if not self.strokes:
            raise InvalidDrawingError("a drawing needs at least one stroke")
        if len(self.strokes) > MAX_STROKES_PER_DRAWING:
            raise InvalidDrawingError(
                f"a drawing can have at most {MAX_STROKES_PER_DRAWING} strokes"
            )


class DrawingStorageError(Exception):
    """Raised when a drawing cannot be stored (disk failure, unsafe location...)."""


class DrawingRepository(Protocol):
    def save(self, drawing: Drawing, drawn_on: date) -> str:
        """Stores the drawing as an image and returns the name it was saved under."""
        ...
