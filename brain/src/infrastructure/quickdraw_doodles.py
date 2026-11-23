"""Doodles from Google's Quick, Draw! dataset (CC BY 4.0), kept as strokes.

The original files have one JSON drawing per line, where each stroke is
[[x1, x2, ...], [y1, y2, ...]] inside a 255x255 box. Here they become [x, y] pairs, the
format the rest of the brain uses, and only a small sample per category is stored.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from src.domain.doodle import Doodle, DoodleLibrary, DoodleStroke, InvalidDoodleError

QUICKDRAW_CATEGORIES_URL = (
    "https://raw.githubusercontent.com/googlecreativelab/quickdraw-dataset/master/categories.txt"
)
QUICKDRAW_SIMPLIFIED_URL = (
    "https://storage.googleapis.com/quickdraw_dataset/full/simplified/{category}.ndjson"
)
DOODLES_DIR = Path(__file__).resolve().parents[2] / "doodles"
DEFAULT_SAMPLE_FILE = DOODLES_DIR / "quickdraw_sample.json"

_SAMPLE_FILE_CONTENT = TypeAdapter(dict[str, list[list[list[tuple[int, int]]]]])


def doodle_from_quickdraw_line(category: str, line: str) -> Doodle | None:
    """The doodle on one line of a Quick, Draw! file, or None when it should be skipped.

    Skipped: drawings the game did not recognize as the category, and drawings that break
    a board rule (too many strokes or points). Single dots are dropped from the strokes.
    """
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict) or record.get("recognized") is not True:
        return None
    strokes = _strokes_as_pairs(record.get("drawing"))
    if strokes is None:
        return None
    try:
        return Doodle(category=category, strokes=strokes)
    except InvalidDoodleError:
        return None


def sample_doodles(category: str, lines: Iterable[str], limit: int) -> list[Doodle]:
    """The first `limit` usable doodles in the lines; stops reading as soon as it has them."""
    doodles: list[Doodle] = []
    for line in lines:
        doodle = doodle_from_quickdraw_line(category, line)
        if doodle is not None:
            doodles.append(doodle)
        if len(doodles) >= limit:
            break
    return doodles


def save_doodle_sample(
    doodles_by_category: Mapping[str, Sequence[Doodle]], file_path: Path = DEFAULT_SAMPLE_FILE
) -> None:
    content = {
        category: [[list(map(list, stroke)) for stroke in doodle.strokes] for doodle in doodles]
        for category, doodles in doodles_by_category.items()
    }
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(content, separators=(",", ":")), encoding="utf-8")


def load_doodle_library(file_path: Path = DEFAULT_SAMPLE_FILE) -> DoodleLibrary:
    try:
        content = _SAMPLE_FILE_CONTENT.validate_json(file_path.read_bytes())
    except (OSError, ValidationError) as error:
        raise InvalidDoodleError(
            f"could not read the doodle sample {file_path}: {error}"
        ) from error
    return DoodleLibrary(
        {
            category: [
                Doodle(category=category, strokes=tuple(tuple(stroke) for stroke in strokes))
                for strokes in doodles
            ]
            for category, doodles in content.items()
        }
    )


def _strokes_as_pairs(drawing: object) -> tuple[DoodleStroke, ...] | None:
    if not isinstance(drawing, list):
        return None
    strokes: list[DoodleStroke] = []
    for raw_stroke in drawing:
        if not isinstance(raw_stroke, list) or len(raw_stroke) < 2:
            return None
        xs, ys = raw_stroke[0], raw_stroke[1]
        if not isinstance(xs, list) or not isinstance(ys, list) or len(xs) != len(ys):
            return None
        if not all(isinstance(value, int) for value in xs + ys):
            return None
        if len(xs) >= 2:
            strokes.append(tuple(zip(xs, ys, strict=True)))
    return tuple(strokes)
