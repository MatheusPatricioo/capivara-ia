import json
from datetime import date
from pathlib import Path

from src.domain.search_history import SearchHistoryError, search_key

QUERY_FIELD = "query"
SEARCHED_ON_FIELD = "searched_on"


class JsonSearchHistory:
    """Keeps every search the capybara did in a JSON file, keyed by search_key.

    Each entry also stores the original query, so the file stays readable in the Explorer:
    {"buracos negros": {"query": "Buracos negros!", "searched_on": "2026-11-23"}}
    """

    def __init__(self, history_file: Path) -> None:
        self._history_file = history_file

    def last_searched_on(self, query: str) -> date | None:
        entry = self._read_entries().get(search_key(query))
        if entry is None:
            return None
        try:
            return date.fromisoformat(entry[SEARCHED_ON_FIELD])
        except (KeyError, TypeError, ValueError) as error:
            raise SearchHistoryError(f"invalid entry for '{query}': {entry}") from error

    def record(self, query: str, searched_on: date) -> None:
        entries = self._read_entries()
        entries[search_key(query)] = {
            QUERY_FIELD: query,
            SEARCHED_ON_FIELD: searched_on.isoformat(),
        }
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            self._history_file.write_text(
                json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as error:
            raise SearchHistoryError(f"could not write the search history: {error}") from error

    def _read_entries(self) -> dict[str, dict[str, str]]:
        if not self._history_file.is_file():
            return {}
        try:
            entries = json.loads(self._history_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise SearchHistoryError(f"could not read the search history: {error}") from error
        if not isinstance(entries, dict):
            raise SearchHistoryError("the search history file does not hold a JSON object")
        return entries
