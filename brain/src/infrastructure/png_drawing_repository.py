from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    Drawing,
    DrawingStorageError,
    Stroke,
)
from src.infrastructure.safe_file_names import free_dated_file_path, is_inside

FILE_EXTENSION = ".png"
# Like a quick sketch in Paint: a white canvas and a single black brush, always the same width.
CANVAS_COLOR = (255, 255, 255)
PEN_COLOR = (0, 0, 0)
STROKE_WIDTH = 3


class PngDrawingRepository:
    """Renders each drawing as a Paint-style PNG (black on white) in the discoveries folder."""

    def __init__(self, discoveries_dir: Path) -> None:
        self._discoveries_dir = discoveries_dir.resolve()

    def save(self, drawing: Drawing, drawn_on: date) -> str:
        try:
            self._discoveries_dir.mkdir(parents=True, exist_ok=True)
            file_path = free_dated_file_path(
                self._discoveries_dir, drawn_on, drawing.title, FILE_EXTENSION
            )
            self._ensure_inside_discoveries_dir(file_path)
            self._render(drawing).save(file_path, format="PNG")
        except OSError as error:
            raise DrawingStorageError(f"could not save the drawing: {error}") from error
        return file_path.name

    def _render(self, drawing: Drawing) -> Image.Image:
        image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), CANVAS_COLOR)
        pen = ImageDraw.Draw(image)
        for stroke in drawing.strokes:
            self._draw_stroke(pen, stroke)
        return image

    @staticmethod
    def _draw_stroke(pen: ImageDraw.ImageDraw, stroke: Stroke) -> None:
        """Rounded joints keep the corners of a stroke soft, like a mouse-drawn line."""
        points = [(point.x, point.y) for point in stroke.points]
        pen.line(points, fill=PEN_COLOR, width=STROKE_WIDTH, joint="curve")

    def _ensure_inside_discoveries_dir(self, file_path: Path) -> None:
        if not is_inside(self._discoveries_dir, file_path):
            raise DrawingStorageError(
                f"refusing to write outside the discoveries folder: {file_path}"
            )
