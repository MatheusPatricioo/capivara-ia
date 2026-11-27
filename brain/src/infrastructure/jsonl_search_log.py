import json
import logging
from datetime import datetime
from pathlib import Path

from src.domain.search_log import FoundPage, SearchLogError, SearchRecord

logger = logging.getLogger(__name__)

SEARCH_LOG_RELATIVE_PATH = "history/searches.jsonl"
"""Where the log lives inside the discoveries folder."""


class JsonlSearchLog:
    """Writes every search as one JSON line at the end of a .jsonl file.

    Appending never rewrites earlier searches, so a crash can at most break the last line,
    and readers (like the computer screen in Godot) can read it line by line:
    {"searched_at": "2026-11-23T10:15:02-03:00", "query": "fases da lua",
     "results": [{"title": "Fases da Lua", "url": "https://..."}]}
    """

    def __init__(self, log_file: Path) -> None:
        self._log_file = log_file

    def append(self, record: SearchRecord) -> None:
        line = json.dumps(self._to_json(record), ensure_ascii=False)
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            with self._log_file.open("a", encoding="utf-8", newline="\n") as log:
                log.write(line + "\n")
        except OSError as error:
            raise SearchLogError(f"could not write the search log: {error}") from error

    def newest_first(self) -> list[SearchRecord]:
        """Every valid search, the newest first; empty while nothing was searched.

        A broken line (like one cut by a crash) is skipped, so it never hides the rest.
        """
        try:
            lines = self._log_file.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        except (OSError, UnicodeDecodeError) as error:
            raise SearchLogError(f"could not read the search log: {error}") from error
        records = [record for line in lines if (record := self._from_line(line)) is not None]
        return list(reversed(records))

    @staticmethod
    def _from_line(line: str) -> SearchRecord | None:
        if not line.strip():
            return None
        try:
            fields = json.loads(line)
            return SearchRecord(
                searched_at=datetime.fromisoformat(fields["searched_at"]),
                query=str(fields["query"]),
                results=tuple(
                    FoundPage(title=str(page.get("title", "")), url=str(page["url"]))
                    for page in fields.get("results", [])
                ),
            )
        except (ValueError, KeyError, TypeError, AttributeError):
            logger.warning("Skipped a broken line in the search log: %.200r", line)
            return None

    @staticmethod
    def _to_json(record: SearchRecord) -> dict[str, object]:
        return {
            "searched_at": record.searched_at.isoformat(timespec="seconds"),
            "query": record.query,
            "results": [{"title": page.title, "url": page.url} for page in record.results],
        }
