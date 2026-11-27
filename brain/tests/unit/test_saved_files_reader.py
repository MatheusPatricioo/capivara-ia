import os
from datetime import datetime
from pathlib import Path

import pytest

from src.infrastructure.saved_files_reader import (
    SavedFileNotFoundError,
    SavedFilesReader,
    SavedFileUnreadableError,
    title_from_file_name,
)

OLDER = datetime(2026, 11, 22, 9, 0).timestamp()
NEWER = datetime(2026, 11, 23, 14, 30).timestamp()
FIREFLY_NOTE = "# Vaga-lumes no jardim à noite\n\n- **Data:** 2026-11-23\n"
BUILT_SUGGESTION = "# Uma lousa maior\n\n- **Situação:** construída\n"
WAITING_SUGGESTION = "# Um banco\n\n- **Situação:** pendente\n"


def save_file(folder: Path, file_name: str, content: str | bytes, changed_at: float) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    saved_file = folder / file_name
    if isinstance(content, bytes):
        saved_file.write_bytes(content)
    else:
        saved_file.write_text(content, encoding="utf-8")
    os.utime(saved_file, (changed_at, changed_at))
    return saved_file


@pytest.fixture
def discoveries_dir(tmp_path: Path) -> Path:
    return tmp_path / "descobertas"


@pytest.fixture
def reader(discoveries_dir: Path) -> SavedFilesReader:
    return SavedFilesReader(discoveries_dir)


@pytest.fixture
def two_notes(discoveries_dir: Path) -> None:
    save_file(discoveries_dir, "2026-11-22-gato.md", "# Gato\n", OLDER)
    save_file(discoveries_dir, "2026-11-23-vaga-lumes.md", FIREFLY_NOTE, NEWER)


@pytest.fixture
def two_suggestions(discoveries_dir: Path) -> None:
    suggestions_dir = discoveries_dir / "sugestoes"
    save_file(suggestions_dir, "2026-11-22-lousa-maior.md", BUILT_SUGGESTION, OLDER)
    save_file(suggestions_dir, "2026-11-23-banco.md", WAITING_SUGGESTION, NEWER)


@pytest.fixture
def two_drawings(discoveries_dir: Path) -> None:
    save_file(discoveries_dir, "2026-11-22-gato-dormindo.png", b"\x89PNG old", OLDER)
    save_file(discoveries_dir, "2026-11-23-sol.png", b"\x89PNG new", NEWER)


def test_title_from_file_name_leaves_the_date_out() -> None:
    assert title_from_file_name("2026-11-23-gato-dormindo.png") == "gato dormindo"


def test_title_from_file_name_keeps_a_name_without_date() -> None:
    assert title_from_file_name("rascunho-da-lua.md") == "rascunho da lua"


@pytest.mark.usefixtures("two_notes")
def test_lists_notes_the_most_recently_changed_first(reader: SavedFilesReader) -> None:
    assert [note.file_name for note in reader.notes("discoveries")] == [
        "2026-11-23-vaga-lumes.md",
        "2026-11-22-gato.md",
    ]


@pytest.mark.usefixtures("two_notes")
def test_a_note_title_comes_from_its_heading_with_accents(reader: SavedFilesReader) -> None:
    assert reader.notes("discoveries")[0].title == "Vaga-lumes no jardim à noite"


def test_a_note_without_heading_takes_the_title_of_its_file_name(
    reader: SavedFilesReader, discoveries_dir: Path
) -> None:
    save_file(discoveries_dir, "2026-11-23-anotacao-solta.md", "sem titulo", NEWER)

    assert reader.notes("discoveries")[0].title == "anotacao solta"


def test_a_note_tells_when_it_was_last_changed(
    reader: SavedFilesReader, discoveries_dir: Path
) -> None:
    save_file(discoveries_dir, "2026-11-23-sol.md", "# Sol\n", NEWER)

    assert reader.notes("discoveries")[0].saved_at == datetime(2026, 11, 23, 14, 30)


@pytest.mark.usefixtures("two_notes", "two_suggestions")
def test_discoveries_do_not_include_the_suggestions(reader: SavedFilesReader) -> None:
    assert len(reader.notes("discoveries")) == 2


@pytest.mark.usefixtures("two_suggestions")
def test_a_built_suggestion_is_done(reader: SavedFilesReader) -> None:
    assert reader.note("suggestions", "2026-11-22-lousa-maior.md").done is True


@pytest.mark.usefixtures("two_suggestions")
def test_a_waiting_suggestion_is_not_done(reader: SavedFilesReader) -> None:
    assert reader.note("suggestions", "2026-11-23-banco.md").done is False


def test_lists_no_notes_when_the_folder_does_not_exist(reader: SavedFilesReader) -> None:
    assert reader.notes("discoveries") == []


@pytest.mark.usefixtures("two_notes")
def test_reads_the_text_of_a_note(reader: SavedFilesReader) -> None:
    assert reader.note_text("discoveries", "2026-11-23-vaga-lumes.md") == FIREFLY_NOTE


@pytest.mark.usefixtures("two_notes")
def test_reading_a_missing_note_raises_not_found(reader: SavedFilesReader) -> None:
    with pytest.raises(SavedFileNotFoundError):
        reader.note_text("discoveries", "2026-11-23-nao-existe.md")


@pytest.mark.usefixtures("two_drawings")
def test_a_drawing_is_not_read_as_a_note(reader: SavedFilesReader) -> None:
    with pytest.raises(SavedFileNotFoundError):
        reader.note_text("discoveries", "2026-11-23-sol.png")


def test_reading_a_note_with_broken_encoding_raises_unreadable(
    reader: SavedFilesReader, discoveries_dir: Path
) -> None:
    save_file(discoveries_dir, "2026-11-23-quebrada.md", b"\xff\xfe\xfa", NEWER)

    with pytest.raises(SavedFileUnreadableError):
        reader.note_text("discoveries", "2026-11-23-quebrada.md")


@pytest.mark.usefixtures("two_drawings")
def test_lists_drawings_newest_first_with_titles(reader: SavedFilesReader) -> None:
    assert [drawing.title for drawing in reader.drawings()] == ["sol", "gato dormindo"]


@pytest.mark.usefixtures("two_drawings")
def test_reads_the_bytes_of_a_drawing(reader: SavedFilesReader) -> None:
    assert reader.drawing_png("2026-11-23-sol.png") == b"\x89PNG new"


@pytest.mark.usefixtures("two_drawings")
def test_reading_a_missing_drawing_raises_not_found(reader: SavedFilesReader) -> None:
    with pytest.raises(SavedFileNotFoundError):
        reader.drawing_png("2026-11-23-lua.png")
