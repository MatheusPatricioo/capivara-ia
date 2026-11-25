"""Her diary in the discoveries folder: one Markdown file per day, easy to read in the Explorer.

diario/2026-11-25.md

# Diário de 25/11/2026

## 14:30

Hoje pesquisei sobre vaga-lumes...
"""

import logging
import re
from datetime import date, datetime, time
from pathlib import Path

from src.domain.diary import DiaryDay, DiaryEntry, DiaryStorageError, InvalidDiaryEntryError
from src.infrastructure.safe_file_names import is_inside

logger = logging.getLogger(__name__)

DIARY_FOLDER_NAME = "diario"
"""A subfolder, so the diary never mixes with the discoveries (which are only top-level files)."""
FILE_EXTENSION = ".md"
TITLE_DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"
ENTRY_HEADING_PREFIX = "## "
# Only files named like 2026-11-25.md are pages of the diary; anything else is ignored.
DAY_FILE_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


class MarkdownDiary:
    def __init__(self, discoveries_dir: Path) -> None:
        self._diary_dir = discoveries_dir.resolve() / DIARY_FOLDER_NAME

    def write(self, entry: DiaryEntry) -> None:
        file_path = self._diary_dir / f"{entry.written_at.date().isoformat()}{FILE_EXTENSION}"
        if not is_inside(self._diary_dir, file_path):
            raise DiaryStorageError(f"refusing to write outside the diary: {file_path}")
        try:
            self._diary_dir.mkdir(parents=True, exist_ok=True)
            is_new_page = not file_path.exists()
            with file_path.open("a", encoding="utf-8") as page:
                if is_new_page:
                    page.write(_page_title(entry.written_at.date()))
                page.write(_entry_markdown(entry))
        except OSError as error:
            raise DiaryStorageError(f"could not write in the diary: {error}") from error

    def recent_days(self, limit: int) -> list[DiaryDay]:
        """A page that cannot be read is skipped (logged), so one bad file hides nothing else."""
        if not self._diary_dir.is_dir():
            return []
        day_files = sorted(
            (path for path in self._diary_dir.iterdir() if DAY_FILE_NAME.match(path.name)),
            reverse=True,
        )
        days: list[DiaryDay] = []
        for day_file in day_files:
            if len(days) == limit:
                break
            try:
                days.append(_read_day(day_file))
            except DiaryStorageError as error:
                logger.warning("Skipping the diary page %s: %s", day_file.name, error)
        return days


def _page_title(day: date) -> str:
    return f"# Diário de {day.strftime(TITLE_DATE_FORMAT)}\n"


def _entry_markdown(entry: DiaryEntry) -> str:
    return f"\n{ENTRY_HEADING_PREFIX}{entry.written_at.strftime(TIME_FORMAT)}\n\n{entry.text}\n"


def _read_day(day_file: Path) -> DiaryDay:
    try:
        day = date.fromisoformat(day_file.stem)
        lines = day_file.read_text(encoding="utf-8").splitlines()
        entries = tuple(_entries(day, lines))
    except (OSError, ValueError, InvalidDiaryEntryError) as error:
        raise DiaryStorageError(str(error)) from error
    return DiaryDay(day, entries)


def _entries(day: date, lines: list[str]) -> list[DiaryEntry]:
    """Every "## HH:MM" heading starts an entry; its text runs until the next heading."""
    entries: list[DiaryEntry] = []
    current_time: time | None = None
    current_lines: list[str] = []
    for line in lines:
        if line.startswith(ENTRY_HEADING_PREFIX):
            if current_time is not None:
                entries.append(_entry(day, current_time, current_lines))
            current_time = _heading_time(line)
            current_lines = []
        elif current_time is not None:
            current_lines.append(line)
    if current_time is not None:
        entries.append(_entry(day, current_time, current_lines))
    return entries


def _heading_time(heading_line: str) -> time:
    """Reads the time of a heading like "## 14:30". Raises ValueError for any other heading."""
    time_text = heading_line.removeprefix(ENTRY_HEADING_PREFIX).strip()
    return datetime.strptime(time_text, TIME_FORMAT).time()


def _entry(day: date, written_time: time, lines: list[str]) -> DiaryEntry:
    return DiaryEntry(datetime.combine(day, written_time), "\n".join(lines))
