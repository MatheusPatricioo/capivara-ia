import logging
from datetime import datetime
from pathlib import Path

from src.domain.letter import (
    InvalidLetterError,
    Letter,
    LetterStatus,
    LetterStorageError,
    SavedLetter,
)
from src.infrastructure.markdown_notes import first_value_after, section_lines
from src.infrastructure.safe_file_names import free_dated_file_path, is_inside

logger = logging.getLogger(__name__)

LETTERS_FOLDER_NAME = "cartas"
"""A subfolder, so letters never mix with the discoveries (which are only top-level files)."""
FILE_EXTENSION = ".md"
FILE_TITLE = "carta para o matheus"
WRITTEN_AT_FORMAT = "%Y-%m-%d %H:%M"
# The Markdown layout, shared by writing and reading so both always agree.
TITLE_LINE = "# Carta para o Matheus"
WRITTEN_AT_PREFIX = "- **Escrita em:** "
STATUS_PREFIX = "- **Situação:** "
LETTER_HEADING = "## Carta"
STATUS_WORDS = {LetterStatus.UNREAD: "não lida", LetterStatus.READ: "lida"}
# Typed by hand, the accent is easy to forget: "nao lida" counts as unread too.
UNREAD_SPELLINGS = frozenset({"não lida", "nao lida"})


class MarkdownMailbox:
    """The mailbox of her world: one Markdown file per letter in the "cartas" folder.

    Easy to read in the Explorer too. A letter becomes read when Matheus opens it in the
    mailbox of the world (or when its "Situação" line is changed to "lida" by hand).
    """

    def __init__(self, discoveries_dir: Path) -> None:
        self._letters_dir = discoveries_dir.resolve() / LETTERS_FOLDER_NAME

    def post(self, letter: Letter) -> str:
        try:
            self._letters_dir.mkdir(parents=True, exist_ok=True)
            file_path = free_dated_file_path(
                self._letters_dir, letter.written_at.date(), FILE_TITLE, FILE_EXTENSION
            )
            if not is_inside(self._letters_dir, file_path):
                raise LetterStorageError(f"refusing to write outside the letters: {file_path}")
            with file_path.open("x", encoding="utf-8") as letter_file:
                letter_file.write(_to_markdown(letter))
        except OSError as error:
            raise LetterStorageError(f"could not post the letter: {error}") from error
        return file_path.name

    def saved_letters(self) -> list[SavedLetter]:
        """Every letter, the oldest first. A file that is not a letter is skipped (logged)."""
        if not self._letters_dir.is_dir():
            return []
        saved: list[SavedLetter] = []
        for letter_file in self._letters_dir.glob(f"*{FILE_EXTENSION}"):
            try:
                saved.append(SavedLetter(letter_file.name, _read(letter_file)))
            except LetterStorageError as error:
                logger.warning("Skipping %s: %s", letter_file.name, error)
        return sorted(saved, key=lambda saved_letter: saved_letter.letter.written_at)

    def mark_read(self, file_name: str) -> SavedLetter:
        file_path = self._letters_dir / file_name
        if not is_inside(self._letters_dir, file_path):
            raise LetterStorageError(f"refusing to touch a file outside the letters: {file_name}")
        opened = _read(file_path).opened()
        try:
            file_path.write_text(_to_markdown(opened), encoding="utf-8")
        except OSError as error:
            raise LetterStorageError(f"could not update {file_name}: {error}") from error
        return SavedLetter(file_name, opened)


def _read(letter_file: Path) -> Letter:
    try:
        lines = letter_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise LetterStorageError(f"could not read {letter_file.name}: {error}") from error
    try:
        return _from_markdown(lines)
    except (InvalidLetterError, ValueError) as error:
        raise LetterStorageError(f"{letter_file.name} is not a letter: {error}") from error


def _to_markdown(letter: Letter) -> str:
    return (
        f"{TITLE_LINE}\n\n"
        f"{WRITTEN_AT_PREFIX}{letter.written_at.strftime(WRITTEN_AT_FORMAT)}\n"
        f"{STATUS_PREFIX}{STATUS_WORDS[letter.status]}\n\n"
        f"{LETTER_HEADING}\n\n"
        f"{letter.text}\n"
    )


def _from_markdown(lines: list[str]) -> Letter:
    """Reads back what _to_markdown wrote. Raises ValueError or InvalidLetterError."""
    written_at_text = first_value_after(WRITTEN_AT_PREFIX, lines)
    return Letter(
        written_at=datetime.strptime(written_at_text, WRITTEN_AT_FORMAT),
        text="\n".join(section_lines(LETTER_HEADING, lines)),
        status=_status(first_value_after(STATUS_PREFIX, lines)),
    )


def _status(status_text: str) -> LetterStatus:
    if status_text.lower() in UNREAD_SPELLINGS:
        return LetterStatus.UNREAD
    return LetterStatus.READ
