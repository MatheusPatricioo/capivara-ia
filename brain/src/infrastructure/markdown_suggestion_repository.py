import logging
from datetime import date
from pathlib import Path

from src.domain.world_suggestion import (
    InvalidSuggestionError,
    SavedSuggestion,
    SuggestionStatus,
    SuggestionStorageError,
    WorldSuggestion,
)
from src.infrastructure.markdown_notes import first_value_after, section_lines
from src.infrastructure.safe_file_names import free_dated_file_path, is_inside

logger = logging.getLogger(__name__)

SUGGESTIONS_FOLDER_NAME = "sugestoes"
"""A subfolder, so suggestions never mix with the discoveries (which are only top-level files)."""
FILE_EXTENSION = ".md"
# The Markdown layout, shared by writing and reading so both always agree.
TITLE_PREFIX = "# "
DATE_PREFIX = "- **Data:** "
INSPIRED_BY_PREFIX = "- **Inspirada em:** "
STATUS_PREFIX = "- **Situação:** "
WORLD_THING_PREFIX = "- **No mundo:** "
REASON_HEADING = "## Por que eu quero"
# Typed by hand, the accent is easy to forget: "construida" counts as built too.
BUILT_STATUS_SPELLINGS = frozenset({"construída", "construida"})


class MarkdownSuggestionRepository:
    """Saves each suggestion as a Markdown file in the "sugestoes" folder of the discoveries.

    One file per suggestion, easy to read in the Explorer: the developer goes through them,
    builds in the world the ones that make sense and marks them as built (by hand, changing
    the "Situação" line, or with python -m src.mark_suggestion_built).
    """

    def __init__(self, discoveries_dir: Path) -> None:
        self._discoveries_dir = discoveries_dir.resolve()
        self._suggestions_dir = self._discoveries_dir / SUGGESTIONS_FOLDER_NAME

    def save(self, suggestion: WorldSuggestion) -> str:
        try:
            self._suggestions_dir.mkdir(parents=True, exist_ok=True)
            file_path = free_dated_file_path(
                self._suggestions_dir, suggestion.suggested_on, suggestion.request, FILE_EXTENSION
            )
            self._ensure_inside_suggestions_dir(file_path)
            with file_path.open("x", encoding="utf-8") as suggestion_file:
                suggestion_file.write(_to_markdown(suggestion))
        except OSError as error:
            raise SuggestionStorageError(f"could not save the suggestion: {error}") from error
        return file_path.name

    def saved_suggestions(self) -> list[SavedSuggestion]:
        """Every suggestion file, the oldest first (names start with the date).

        A file that cannot be read, or is not a suggestion (a note dropped in by hand), is
        skipped with a warning: an odd file must not stop her from suggesting.
        """
        if not self._suggestions_dir.is_dir():
            return []
        saved: list[SavedSuggestion] = []
        for suggestion_file in sorted(self._suggestions_dir.glob(f"*{FILE_EXTENSION}")):
            try:
                saved.append(SavedSuggestion(suggestion_file.name, self._read(suggestion_file)))
            except SuggestionStorageError as error:
                logger.warning("Skipping %s: %s", suggestion_file.name, error)
        return saved

    def mark_built(self, file_name: str, world_thing_id: str = "") -> SavedSuggestion:
        """Rewrites the suggestion as built, linked to the world thing when one is given.

        Raises SuggestionStorageError when the file is missing, unreadable or not a
        suggestion, and InvalidSuggestionError when world_thing_id is not a valid id.
        """
        file_path = self._suggestions_dir / file_name
        self._ensure_inside_suggestions_dir(file_path)
        built = self._read(file_path).built(world_thing_id)
        try:
            file_path.write_text(_to_markdown(built), encoding="utf-8")
        except OSError as error:
            raise SuggestionStorageError(f"could not update {file_name}: {error}") from error
        return SavedSuggestion(file_path.name, built)

    def _read(self, file_path: Path) -> WorldSuggestion:
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise SuggestionStorageError(f"could not read {file_path.name}: {error}") from error
        try:
            return _from_markdown(lines)
        except (InvalidSuggestionError, ValueError) as error:
            raise SuggestionStorageError(
                f"{file_path.name} is not a suggestion: {error}"
            ) from error

    def _ensure_inside_suggestions_dir(self, file_path: Path) -> None:
        if not is_inside(self._suggestions_dir, file_path):
            raise SuggestionStorageError(
                f"refusing to touch a file outside the suggestions folder: {file_path}"
            )


def _to_markdown(suggestion: WorldSuggestion) -> str:
    world_thing_line = (
        f"{WORLD_THING_PREFIX}{suggestion.world_thing_id}\n" if suggestion.world_thing_id else ""
    )
    return (
        f"{TITLE_PREFIX}{suggestion.request}\n\n"
        f"{DATE_PREFIX}{suggestion.suggested_on.isoformat()}\n"
        f"{INSPIRED_BY_PREFIX}{suggestion.inspired_by}\n"
        f"{STATUS_PREFIX}{suggestion.status.value}\n"
        f"{world_thing_line}\n"
        f"{REASON_HEADING}\n\n"
        f"{suggestion.reason}\n"
    )


def _from_markdown(lines: list[str]) -> WorldSuggestion:
    """Reads back what _to_markdown wrote. Raises ValueError or InvalidSuggestionError.

    A file without a "Situação" line (written before the status existed) is pending.
    """
    return WorldSuggestion(
        request=first_value_after(TITLE_PREFIX, lines),
        reason="\n".join(section_lines(REASON_HEADING, lines)).strip(),
        inspired_by=first_value_after(INSPIRED_BY_PREFIX, lines),
        suggested_on=date.fromisoformat(first_value_after(DATE_PREFIX, lines)),
        status=_status(first_value_after(STATUS_PREFIX, lines)),
        world_thing_id=first_value_after(WORLD_THING_PREFIX, lines),
    )


def _status(status_text: str) -> SuggestionStatus:
    if status_text.lower() in BUILT_STATUS_SPELLINGS:
        return SuggestionStatus.BUILT
    return SuggestionStatus.PENDING
