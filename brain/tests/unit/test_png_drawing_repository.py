from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from src.domain.drawing import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    Circle,
    Drawing,
    DrawingStorageError,
    Line,
    Point,
    Rectangle,
    Text,
)
from src.infrastructure.png_drawing_repository import (
    BOARD_COLOR,
    CHALK_RGB,
    PngDrawingRepository,
)

DRAWN_ON = date(2026, 11, 23)
EXPECTED_FILE_NAME = "2026-11-23-o-sol-e-o-capim.png"

SUN = Circle(center=Point(200, 150), radius=40, color="yellow")
GROUND = Line(start=Point(0, 250), end=Point(400, 250), color="green")
FRAME = Rectangle(top_left=Point(10, 10), bottom_right=Point(60, 60), color="blue")
LABEL = Text(position=Point(300, 20), content="sol", color="white")
DRAWING = Drawing(title="O sol e o capim", shapes=(SUN, GROUND, FRAME, LABEL))


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

    assert repository.save(DRAWING, DRAWN_ON) == "2026-11-23-o-sol-e-o-capim-2.png"


def test_image_has_the_size_of_the_chalkboard(saved_image: Image.Image) -> None:
    assert saved_image.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_empty_area_keeps_the_board_color(saved_image: Image.Image) -> None:
    assert saved_image.getpixel((100, 200)) == BOARD_COLOR


def test_draws_the_circle_outline_with_its_chalk(saved_image: Image.Image) -> None:
    assert saved_image.getpixel((239, 150)) == CHALK_RGB["yellow"]


def test_leaves_the_inside_of_the_circle_empty(saved_image: Image.Image) -> None:
    assert saved_image.getpixel((200, 150)) == BOARD_COLOR


def test_draws_the_line_with_its_chalk(saved_image: Image.Image) -> None:
    assert saved_image.getpixel((200, 250)) == CHALK_RGB["green"]


def test_draws_the_rectangle_border_with_its_chalk(saved_image: Image.Image) -> None:
    assert saved_image.getpixel((10, 35)) == CHALK_RGB["blue"]


def test_writes_the_text_with_its_chalk(saved_image: Image.Image) -> None:
    text_area = saved_image.crop((300, 20, 360, 50))
    colors_in_area = text_area.getcolors(maxcolors=text_area.width * text_area.height) or []

    assert CHALK_RGB["white"] in [color for _, color in colors_in_area]


def test_raises_a_storage_error_when_the_folder_cannot_be_created(tmp_path: Path) -> None:
    blocking_file = tmp_path / "not-a-folder"
    blocking_file.write_text("", encoding="utf-8")
    repository = PngDrawingRepository(blocking_file)

    with pytest.raises(DrawingStorageError):
        repository.save(DRAWING, DRAWN_ON)


def rendered_text(repository: PngDrawingRepository, discoveries_dir: Path, content: str) -> bytes:
    text = Text(position=Point(20, 100), content=content, color="white")
    file_name = repository.save(Drawing(title=content, shapes=(text,)), DRAWN_ON)
    return Image.open(discoveries_dir / file_name).convert("RGB").tobytes()


def test_writes_accented_letters_instead_of_a_missing_glyph_box(
    repository: PngDrawingRepository, discoveries_dir: Path
) -> None:
    """A font without accents draws the same empty box for every accented letter."""
    with_tilde = rendered_text(repository, discoveries_dir, "ã")
    with_acute = rendered_text(repository, discoveries_dir, "é")

    assert with_tilde != with_acute
