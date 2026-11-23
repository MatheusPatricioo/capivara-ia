from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    Drawing,
    DrawingStorageError,
    Point,
    Stroke,
)
from src.infrastructure.png_drawing_repository import (
    CANVAS_COLOR,
    PEN_COLOR,
    PngDrawingRepository,
)

DRAWN_ON = date(2026, 11, 23)
EXPECTED_FILE_NAME = "2026-11-23-o-capim.png"

GROUND = Stroke(points=(Point(0, 250), Point(400, 250)))
GRASS_BLADE = Stroke(points=(Point(100, 250), Point(110, 200), Point(120, 250)))
DRAWING = Drawing(title="O capim", strokes=(GROUND, GRASS_BLADE))


@pytest.fixture
def discoveries_dir(tmp_path: Path) -> Path:
    return tmp_path / "discoveries"


@pytest.fixture
def repository(discoveries_dir: Path) -> PngDrawingRepository:
    return PngDrawingRepository(discoveries_dir)


@pytest.fixture
def saved_image(repository: PngDrawingRepository, discoveries_dir: Path) -> Image.Image:
    file_name = repository.save(DRAWING, DRAWN_ON)
    return Image.open(discoveries_dir / file_name).convert("RGB")


def test_names_the_file_with_the_date_and_the_title_slug(
    repository: PngDrawingRepository,
) -> None:
    assert repository.save(DRAWING, DRAWN_ON) == EXPECTED_FILE_NAME


def test_never_overwrites_an_existing_drawing(repository: PngDrawingRepository) -> None:
    repository.save(DRAWING, DRAWN_ON)

    assert repository.save(DRAWING, DRAWN_ON) == "2026-11-23-o-capim-2.png"


def test_image_has_the_size_of_the_chalkboard(saved_image: Image.Image) -> None:
    assert saved_image.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_empty_area_keeps_the_white_canvas(saved_image: Image.Image) -> None:
    assert saved_image.getpixel((300, 100)) == CANVAS_COLOR


def test_draws_a_straight_stroke_with_the_black_pen(saved_image: Image.Image) -> None:
    assert saved_image.getpixel((300, 250)) == PEN_COLOR


def test_draws_a_stroke_through_its_middle_point(saved_image: Image.Image) -> None:
    assert saved_image.getpixel((110, 201)) == PEN_COLOR


def test_uses_only_the_canvas_and_the_pen_colors(saved_image: Image.Image) -> None:
    """A single brush: no other color appears."""
    pixel_count = saved_image.width * saved_image.height
    colors = {color for _, color in saved_image.getcolors(maxcolors=pixel_count) or []}

    assert colors <= {CANVAS_COLOR, PEN_COLOR}


def test_raises_a_storage_error_when_the_folder_cannot_be_created(tmp_path: Path) -> None:
    blocking_file = tmp_path / "not-a-folder"
    blocking_file.write_text("", encoding="utf-8")
    repository = PngDrawingRepository(blocking_file)

    with pytest.raises(DrawingStorageError):
        repository.save(DRAWING, DRAWN_ON)
