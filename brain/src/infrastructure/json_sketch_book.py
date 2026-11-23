from pathlib import Path

from pydantic import BaseModel, TypeAdapter, ValidationError

from src.domain.sketch import InvalidSketchError, Sketch, SketchBook

SKETCHES_DIR = Path(__file__).resolve().parents[2] / "sketches"
DEFAULT_SKETCH_BOOK_FILE = SKETCHES_DIR / "sketch_book.json"


class _SketchEntry(BaseModel):
    name: str
    description: str
    strokes: list[list[tuple[int, int]]]


_SKETCH_ENTRIES = TypeAdapter(list[_SketchEntry])


def load_sketch_book(file_path: Path = DEFAULT_SKETCH_BOOK_FILE) -> SketchBook:
    """Reads the capybara's sketches from a JSON file: a list of {name, description, strokes}.

    Each stroke is a list of [x, y] points inside a 100x100 box. Adding a sketch to the file
    is enough for her to know how to draw it.
    """
    try:
        entries = _SKETCH_ENTRIES.validate_json(file_path.read_bytes())
    except (OSError, ValidationError) as error:
        raise InvalidSketchError(f"could not read the sketch book {file_path}: {error}") from error
    return SketchBook(
        Sketch(
            name=entry.name,
            description=entry.description,
            strokes=tuple(tuple(stroke) for stroke in entry.strokes),
        )
        for entry in entries
    )
