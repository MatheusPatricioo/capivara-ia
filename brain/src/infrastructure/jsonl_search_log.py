import json
from pathlib import Path

from src.domain.search_log import SearchLogError, SearchRecord


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

    @staticmethod
    def _to_json(record: SearchRecord) -> dict[str, object]:
        return {
            "searched_at": record.searched_at.isoformat(timespec="seconds"),
            "query": record.query,
            "results": [{"title": page.title, "url": page.url} for page in record.results],
        }
