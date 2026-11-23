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
from src.infrastructure.markdown_discovery_repository import slugify

FILE_EXTENSION = ".png"
BOARD_COLOR = (47, 79, 58)
# Her single brush: white chalk, always the same width.
CHALK_COLOR = (240, 240, 235)
STROKE_WIDTH = 3


class PngDrawingRepository:
    """Renders each drawing as a chalkboard-style PNG inside the discoveries folder."""

    def __init__(self, discoveries_dir: Path) -> None:
        self._discoveries_dir = discoveries_dir.resolve()

    def save(self, drawing: Drawing, drawn_on: date) -> str:
        try:
            self._discoveries_dir.mkdir(parents=True, exist_ok=True)
            file_path = self._free_file_path(drawing, drawn_on)
            self._ensure_inside_discoveries_dir(file_path)
            self._render(drawing).save(file_path, format="PNG")
        except OSError as error:
            raise DrawingStorageError(f"could not save the drawing: {error}") from error
        return file_path.name

    def _render(self, drawing: Drawing) -> Image.Image:
        image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), BOARD_COLOR)
        pen = ImageDraw.Draw(image)
        for stroke in drawing.strokes:
            self._draw_stroke(pen, stroke)
        return image

    @staticmethod
    def _draw_stroke(pen: ImageDraw.ImageDraw, stroke: Stroke) -> None:
        """Rounded joints keep the corners of a stroke soft, like real chalk."""
        points = [(point.x, point.y) for point in stroke.points]
        pen.line(points, fill=CHALK_COLOR, width=STROKE_WIDTH, joint="curve")

    def _free_file_path(self, drawing: Drawing, drawn_on: date) -> Path:
        """Builds date + slug, adding -2, -3... so an existing file is never overwritten."""
        base_name = f"{drawn_on.isoformat()}-{slugify(drawing.title)}"
        file_path = self._discoveries_dir / f"{base_name}{FILE_EXTENSION}"
        copy_number = 2
        while file_path.exists():
            file_path = self._discoveries_dir / f"{base_name}-{copy_number}{FILE_EXTENSION}"
            copy_number += 1
        return file_path

    def _ensure_inside_discoveries_dir(self, file_path: Path) -> None:
        """Defense in depth: the slug already blocks traversal, this double-checks it."""
        if not file_path.resolve().is_relative_to(self._discoveries_dir):
            raise DrawingStorageError(
                f"refusing to write outside the discoveries folder: {file_path}"
            )
