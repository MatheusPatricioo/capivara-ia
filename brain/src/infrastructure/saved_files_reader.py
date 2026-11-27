"""Reads what the capybara saved (notes and drawings) for a visual client to show.

Only the brain knows how files are named and laid out, so titles are made here and the
client only ever sees an opaque id (the file name) and a ready title.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.infrastructure.markdown_discovery_repository import TITLE_PREFIX
from src.infrastructure.markdown_notes import first_value_after
from src.infrastructure.markdown_suggestion_repository import (
    BUILT_STATUS_SPELLINGS,
    STATUS_PREFIX,
    SUGGESTIONS_FOLDER_NAME,
)
from src.infrastructure.safe_file_names import is_inside
from src.infrastructure.world_requests import DiscoveryFolder

NOTE_EXTENSION = ".md"
DRAWING_EXTENSION = ".png"
DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")


@dataclass(frozen=True)
class SavedFile:
    file_name: str
    title: str
    saved_at: datetime
    """When the file last changed, in local time."""
    done: bool = False


class SavedFileError(Exception):
    """Base for failures reading a saved file."""


class SavedFileNotFoundError(SavedFileError):
    """The file does not exist in the folder (or is not of the asked kind)."""


class SavedFileUnreadableError(SavedFileError):
    """The file exists but could not be read (disk failure, broken encoding...)."""


def title_from_file_name(file_name: str) -> str:
    """ "2026-11-23-gato-dormindo.png" becomes "gato dormindo"."""
    return DATE_PREFIX.sub("", Path(file_name).stem).replace("-", " ")


class SavedFilesReader:
    """Reads only top-level files of the discoveries folder and of its suggestions folder."""

    def __init__(self, discoveries_dir: Path) -> None:
        self._discoveries_dir = discoveries_dir.resolve()

    def folder_path(self, folder: DiscoveryFolder) -> Path:
        if folder == "suggestions":
            return self._discoveries_dir / SUGGESTIONS_FOLDER_NAME
        return self._discoveries_dir

    def notes(self, folder: DiscoveryFolder) -> list[SavedFile]:
        """The notes of the folder, the most recently changed first."""
        return [
            self._note_summary(note_file, folder)
            for note_file in self._newest_first(self.folder_path(folder), NOTE_EXTENSION)
        ]

    def note(self, folder: DiscoveryFolder, file_name: str) -> SavedFile:
        """The same summary the list gives, for one note."""
        note_file = self._existing_file(self.folder_path(folder), file_name, NOTE_EXTENSION)
        return self._note_summary(note_file, folder)

    def note_text(self, folder: DiscoveryFolder, file_name: str) -> str:
        note_file = self._existing_file(self.folder_path(folder), file_name, NOTE_EXTENSION)
        try:
            return note_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise SavedFileUnreadableError(f"could not read {file_name}: {error}") from error

    def drawings(self) -> list[SavedFile]:
        """Her drawings, the most recently changed first."""
        return [
            self._drawing_summary(drawing_file)
            for drawing_file in self._newest_first(self._discoveries_dir, DRAWING_EXTENSION)
        ]

    def drawing(self, file_name: str) -> SavedFile:
        """The same summary the list gives, for one drawing."""
        drawing_file = self._existing_file(self._discoveries_dir, file_name, DRAWING_EXTENSION)
        return self._drawing_summary(drawing_file)

    def drawing_png(self, file_name: str) -> bytes:
        drawing_file = self._existing_file(self._discoveries_dir, file_name, DRAWING_EXTENSION)
        try:
            return drawing_file.read_bytes()
        except OSError as error:
            raise SavedFileUnreadableError(f"could not read {file_name}: {error}") from error

    def _note_summary(self, note_file: Path, folder: DiscoveryFolder) -> SavedFile:
        """A note that cannot be read is still listed, under the title of its file name."""
        try:
            lines = note_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            lines = []
        return SavedFile(
            file_name=note_file.name,
            # The note's own title keeps the accents the file name lost.
            title=first_value_after(TITLE_PREFIX, lines) or title_from_file_name(note_file.name),
            saved_at=self._changed_at(note_file),
            done=folder == "suggestions" and self._is_built(lines),
        )

    def _drawing_summary(self, drawing_file: Path) -> SavedFile:
        return SavedFile(
            file_name=drawing_file.name,
            title=title_from_file_name(drawing_file.name),
            saved_at=self._changed_at(drawing_file),
        )

    @staticmethod
    def _is_built(lines: list[str]) -> bool:
        return first_value_after(STATUS_PREFIX, lines).lower() in BUILT_STATUS_SPELLINGS

    def _newest_first(self, folder_path: Path, extension: str) -> list[Path]:
        """Newer files first; files changed in the same second fall back to the name,
        whose date prefix puts the newest first too."""
        if not folder_path.is_dir():
            return []
        files = [found for found in folder_path.glob(f"*{extension}") if found.is_file()]
        return sorted(
            files, key=lambda found: (int(found.stat().st_mtime), found.name), reverse=True
        )

    def _existing_file(self, folder_path: Path, file_name: str, extension: str) -> Path:
        file_path = folder_path / file_name
        if (
            Path(file_name).suffix != extension
            or not is_inside(folder_path, file_path)
            or not file_path.is_file()
        ):
            raise SavedFileNotFoundError(f"no {extension} file named {file_name}")
        return file_path

    @staticmethod
    def _changed_at(saved_file: Path) -> datetime:
        return datetime.fromtimestamp(saved_file.stat().st_mtime)
