from datetime import date
from pathlib import Path
from typing import assert_never

from PIL import Image, ImageDraw, ImageFont

from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    Circle,
    Drawing,
    DrawingStorageError,
    Line,
    Rectangle,
    Shape,
    Text,
)
from src.infrastructure.markdown_discovery_repository import slugify

FILE_EXTENSION = ".png"
BOARD_COLOR = (47, 79, 58)
CHALK_RGB = {
    "white": (240, 240, 235),
    "yellow": (245, 225, 120),
    "pink": (240, 160, 190),
    "blue": (140, 190, 240),
    "green": (160, 220, 150),
}
STROKE_WIDTH = 3
FONT_SIZE = 22
# A free (OFL) handwriting font shipped with the project: Pillow's default font has no
# accented letters, so 'corações' came out as 'cora□□es'.
FONTS_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
DEFAULT_FONT_FILE = FONTS_DIR / "PatrickHand-Regular.ttf"


class PngDrawingRepository:
    """Renders each drawing as a chalkboard-style PNG inside the discoveries folder."""

    def __init__(self, discoveries_dir: Path, font_file: Path = DEFAULT_FONT_FILE) -> None:
        self._discoveries_dir = discoveries_dir.resolve()
        self._font = ImageFont.truetype(font_file, FONT_SIZE)

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
        for shape in drawing.shapes:
            self._draw_shape(pen, shape)
        return image

    def _draw_shape(self, pen: ImageDraw.ImageDraw, shape: Shape) -> None:
        match shape:
            case Line(start=start, end=end, color=color):
                pen.line(
                    [(start.x, start.y), (end.x, end.y)], fill=CHALK_RGB[color], width=STROKE_WIDTH
                )
            case Circle(center=center, radius=radius, color=color):
                bounding_box = (
                    center.x - radius,
                    center.y - radius,
                    center.x + radius,
                    center.y + radius,
                )
                pen.ellipse(bounding_box, outline=CHALK_RGB[color], width=STROKE_WIDTH)
            case Rectangle(top_left=top_left, bottom_right=bottom_right, color=color):
                pen.rectangle(
                    (top_left.x, top_left.y, bottom_right.x, bottom_right.y),
                    outline=CHALK_RGB[color],
                    width=STROKE_WIDTH,
                )
            case Text(position=position, content=content, color=color):
                pen.text((position.x, position.y), content, fill=CHALK_RGB[color], font=self._font)
            case _:
                assert_never(shape)

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
