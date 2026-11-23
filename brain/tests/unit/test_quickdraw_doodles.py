import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.domain.doodle import Doodle, InvalidDoodleError
from src.infrastructure.quickdraw_doodles import (
    doodle_from_quickdraw_line,
    load_doodle_library,
    sample_doodles,
    save_doodle_sample,
)


def quickdraw_line(drawing: object, recognized: bool = True) -> str:
    """One line of a Quick, Draw! simplified file: each stroke is [[x...], [y...]]."""
    return json.dumps({"word": "cat", "recognized": recognized, "drawing": drawing})


TRIANGLE = [[[10, 50, 90, 10], [80, 10, 80, 80]]]
TRIANGLE_LINE = quickdraw_line(TRIANGLE)


def test_turns_each_stroke_into_x_y_pairs() -> None:
    doodle = doodle_from_quickdraw_line("cat", TRIANGLE_LINE)

    assert doodle == Doodle(category="cat", strokes=(((10, 80), (50, 10), (90, 80), (10, 80)),))


def test_skips_a_drawing_the_game_did_not_recognize() -> None:
    assert doodle_from_quickdraw_line("cat", quickdraw_line(TRIANGLE, recognized=False)) is None


def test_drops_strokes_that_are_a_single_dot() -> None:
    drawing = [*TRIANGLE, [[5], [5]]]

    doodle = doodle_from_quickdraw_line("cat", quickdraw_line(drawing))

    assert doodle is not None and len(doodle.strokes) == 1


def test_skips_a_drawing_with_a_stroke_too_long_for_the_board() -> None:
    long_stroke = [[list(range(41)), [10] * 41]]

    assert doodle_from_quickdraw_line("cat", quickdraw_line(long_stroke)) is None


def test_skips_a_line_that_is_not_json() -> None:
    assert doodle_from_quickdraw_line("cat", "not json") is None


def test_takes_only_the_first_usable_doodles() -> None:
    lines = [quickdraw_line(TRIANGLE, recognized=False)] + [TRIANGLE_LINE] * 5

    assert len(sample_doodles("cat", lines, limit=3)) == 3


def test_stops_reading_once_it_has_enough() -> None:
    read_lines: list[str] = []

    def lines_that_record_reads() -> Iterator[str]:
        for line in [TRIANGLE_LINE] * 5:
            read_lines.append(line)
            yield line

    sample_doodles("cat", lines_that_record_reads(), limit=2)

    assert len(read_lines) == 2


def test_loads_what_was_saved(tmp_path: Path) -> None:
    sample_file = tmp_path / "sample.json"
    doodle = Doodle(category="cat", strokes=(((10, 80), (50, 10)),))
    save_doodle_sample({"cat": [doodle]}, sample_file)

    assert load_doodle_library(sample_file).pick("cat") == doodle


def test_raises_when_the_sample_file_is_missing(tmp_path: Path) -> None:
    with pytest.raises(InvalidDoodleError, match="could not read the doodle sample"):
        load_doodle_library(tmp_path / "missing.json")


def test_loads_the_shipped_sample_with_every_category() -> None:
    """The sample in the repo must stay valid, or the brain could not draw."""
    assert len(load_doodle_library().categories) == 345
