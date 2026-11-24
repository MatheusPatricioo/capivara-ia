import logging
from pathlib import Path

from src.domain.world_suggestion import SuggestionStorageError, WorldSuggestion
from src.infrastructure.safe_file_names import free_dated_file_path, is_inside

logger = logging.getLogger(__name__)

SUGGESTIONS_FOLDER_NAME = "sugestoes"
"""A subfolder, so suggestions never mix with the discoveries (which are only top-level files)."""
FILE_EXTENSION = ".md"
TITLE_PREFIX = "# "
DATE_PREFIX = "- **Data:** "
INSPIRED_BY_PREFIX = "- **Inspirada em:** "
REASON_HEADING = "## Por que eu quero"


class MarkdownSuggestionRepository:
    """Saves each suggestion as a Markdown file in the "sugestoes" folder of the discoveries.

    One file per suggestion, easy to read in the Explorer: the developer goes through them
    and builds in the world the ones that make sense.
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
                suggestion_file.write(self._to_markdown(suggestion))
        except OSError as error:
            raise SuggestionStorageError(f"could not save the suggestion: {error}") from error
        return file_path.name

    def saved_requests(self) -> list[str]:
        """The title line of every suggestion file, the oldest first (names start with the date).

        A file that cannot be read, or has no title line (a note dropped in by hand), is
        skipped: an odd file must not stop her from suggesting.
        """
        if not self._suggestions_dir.is_dir():
            return []
        requests: list[str] = []
        for suggestion_file in sorted(self._suggestions_dir.glob(f"*{FILE_EXTENSION}")):
            request = self._read_request(suggestion_file)
            if request:
                requests.append(request)
        return requests

    @staticmethod
    def _read_request(suggestion_file: Path) -> str:
        try:
            lines = suggestion_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            logger.warning("Skipping the unreadable suggestion %s: %s", suggestion_file.name, error)
            return ""
        for line in lines:
            if line.startswith(TITLE_PREFIX):
                return line.removeprefix(TITLE_PREFIX).strip()
        return ""

    def _ensure_inside_suggestions_dir(self, file_path: Path) -> None:
        if not is_inside(self._suggestions_dir, file_path):
            raise SuggestionStorageError(
                f"refusing to write outside the suggestions folder: {file_path}"
            )

    @staticmethod
    def _to_markdown(suggestion: WorldSuggestion) -> str:
        return (
            f"{TITLE_PREFIX}{suggestion.request}\n\n"
            f"{DATE_PREFIX}{suggestion.suggested_on.isoformat()}\n"
            f"{INSPIRED_BY_PREFIX}{suggestion.inspired_by}\n\n"
            f"{REASON_HEADING}\n\n"
            f"{suggestion.reason}\n"
        )
