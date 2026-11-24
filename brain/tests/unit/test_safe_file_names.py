from datetime import date
from pathlib import Path

import pytest

from src.infrastructure.safe_file_names import free_dated_file_path, is_inside, slugify

DAY = date(2026, 11, 24)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    return tmp_path / "discoveries"


def test_slugify_removes_accents_and_symbols() -> None:
    assert slugify("Estrelas & Constelações!!") == "estrelas-constelacoes"


def test_slugify_falls_back_when_nothing_is_left() -> None:
    assert slugify("?!*") == "descoberta"


def test_slugify_cuts_long_text_without_a_trailing_hyphen() -> None:
    # "lago-" has 5 characters, so the cut at 60 lands right after a hyphen.
    assert slugify("lago " * 20) == ("lago-" * 12).rstrip("-")


def test_free_path_starts_with_the_date_and_the_slug(folder: Path) -> None:
    file_path = free_dated_file_path(folder, DAY, "Vaga-lumes", ".md")

    assert file_path == folder / "2026-11-24-vaga-lumes.md"


def test_free_path_adds_a_number_when_the_name_is_taken(folder: Path) -> None:
    folder.mkdir()
    (folder / "2026-11-24-vaga-lumes.md").write_text("", encoding="utf-8")

    file_path = free_dated_file_path(folder, DAY, "Vaga-lumes", ".md")

    assert file_path == folder / "2026-11-24-vaga-lumes-2.md"


def test_a_file_in_the_folder_is_inside_it(folder: Path) -> None:
    assert is_inside(folder, folder / "nota.md")


def test_a_traversal_path_is_not_inside_the_folder(folder: Path) -> None:
    assert not is_inside(folder, folder / ".." / "escaped.md")
