from collections import defaultdict
from datetime import date

from src.domain.diary import DiaryDay, DiaryEntry, DiaryStorageError


class InMemoryDiary:
    """A diary kept in a dictionary of pages, one per day."""

    def __init__(self) -> None:
        self._pages: defaultdict[date, list[DiaryEntry]] = defaultdict(list)

    def write(self, entry: DiaryEntry) -> None:
        self._pages[entry.written_at.date()].append(entry)

    def recent_days(self, limit: int) -> list[DiaryDay]:
        newest_days = sorted(self._pages, reverse=True)[:limit]
        return [DiaryDay(day, tuple(self._pages[day])) for day in newest_days]


class BrokenDiary:
    """A diary whose disk is always full."""

    def write(self, entry: DiaryEntry) -> None:
        raise DiaryStorageError("disk is full")

    def recent_days(self, limit: int) -> list[DiaryDay]:
        raise DiaryStorageError("disk is full")
