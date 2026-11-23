from pathlib import Path

import pytest

from src.domain.sketch import InvalidSketchError
from src.infrastructure.json_sketch_book import load_sketch_book

STAR_JSON = (
    '[{"name": "estrela", "description": "estrela, céu", '
    '"strokes": [[[50, 4], [61, 37], [96, 37]]]}]'
)


@pytest.fixture
def sketch_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "sketch_book.json"
    file_path.write_text(STAR_JSON, encoding="utf-8")
    return file_path


def test_reads_the_sketch_name_and_description(sketch_file: Path) -> None:
    star = load_sketch_book(sketch_file).find("estrela")

    assert star.description == "estrela, céu"


def test_reads_each_stroke_as_points(sketch_file: Path) -> None:
    star = load_sketch_book(sketch_file).find("estrela")

    assert star.strokes == (((50, 4), (61, 37), (96, 37)),)


def test_raises_when_the_file_is_missing(tmp_path: Path) -> None:
    with pytest.raises(InvalidSketchError, match="could not read the sketch book"):
        load_sketch_book(tmp_path / "missing.json")


def test_raises_when_a_point_is_not_a_pair(tmp_path: Path) -> None:
    broken_file = tmp_path / "broken.json"
    broken_file.write_text(
        '[{"name": "x", "description": "x", "strokes": [[[1, 2, 3], [4, 5]]]}]', encoding="utf-8"
    )

    with pytest.raises(InvalidSketchError):
        load_sketch_book(broken_file)


def test_loads_the_capybaras_real_sketch_book() -> None:
    """The shipped file must always be valid, or the brain would not start."""
    assert "estrela" in load_sketch_book().names
