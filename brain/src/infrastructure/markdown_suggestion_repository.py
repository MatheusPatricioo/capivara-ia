from pathlib import Path

from src.domain.world_suggestion import SuggestionStorageError, WorldSuggestion
from src.infrastructure.safe_file_names import free_dated_file_path, is_inside

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
