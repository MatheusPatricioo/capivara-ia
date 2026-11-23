from dataclasses import dataclass
from datetime import date
from typing import Protocol

CANVAS_WIDTH = 400
CANVAS_HEIGHT = 300
CHALK_COLORS = ("white", "yellow", "pink", "blue", "green")
MAX_SHAPES_PER_DRAWING = 30
MAX_TEXT_LENGTH = 40


class InvalidDrawingError(Exception):
    """Raised when a drawing breaks a chalkboard rule (out of the board, unknown chalk...)."""


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
class Line:
    start: Point
    end: Point
    color: str

    def __post_init__(self) -> None:
        _ensure_chalk_color(self.color)


@dataclass(frozen=True)
class Circle:
    center: Point
    radius: int
    color: str

    def __post_init__(self) -> None:
        _ensure_chalk_color(self.color)
        if self.radius <= 0:
            raise InvalidDrawingError(f"circle radius must be positive, got {self.radius}")


@dataclass(frozen=True)
class Rectangle:
    top_left: Point
    bottom_right: Point
    color: str

    def __post_init__(self) -> None:
        _ensure_chalk_color(self.color)
        if self.top_left.x >= self.bottom_right.x or self.top_left.y >= self.bottom_right.y:
            raise InvalidDrawingError("rectangle top_left must be above and left of bottom_right")


@dataclass(frozen=True)
class Text:
    position: Point
    content: str
    color: str

    def __post_init__(self) -> None:
        _ensure_chalk_color(self.color)
        if not self.content.strip():
            raise InvalidDrawingError("text content must not be empty")
        if len(self.content) > MAX_TEXT_LENGTH:
            raise InvalidDrawingError(f"text content must have at most {MAX_TEXT_LENGTH} chars")


Shape = Line | Circle | Rectangle | Text


@dataclass(frozen=True)
class Drawing:
    title: str
    shapes: tuple[Shape, ...]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise InvalidDrawingError("drawing title must not be empty")
        if not self.shapes:
            raise InvalidDrawingError("a drawing needs at least one shape")
        if len(self.shapes) > MAX_SHAPES_PER_DRAWING:
            raise InvalidDrawingError(f"a drawing can have at most {MAX_SHAPES_PER_DRAWING} shapes")


class DrawingStorageError(Exception):
    """Raised when a drawing cannot be stored (disk failure, unsafe location...)."""


class DrawingRepository(Protocol):
    def save(self, drawing: Drawing, drawn_on: date) -> str:
        """Stores the drawing as an image and returns the name it was saved under."""
        ...


def _ensure_chalk_color(color: str) -> None:
    if color not in CHALK_COLORS:
        raise InvalidDrawingError(
            f"unknown chalk color '{color}', use one of: {', '.join(CHALK_COLORS)}"
        )
