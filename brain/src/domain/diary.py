"""Her personal diary: at the end of each free cycle, she writes what she thought or did."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

MAX_DIARY_ENTRY_LENGTH = 2000


class InvalidDiaryEntryError(ValueError):
    """Raised when an entry breaks a rule (empty or too long)."""


class DiaryStorageError(Exception):
    """Raised when the diary cannot be read or written."""


@dataclass(frozen=True)
class DiaryEntry:
    written_at: datetime
    text: str

    def __post_init__(self) -> None:
        stripped = self.text.strip()
        if not stripped:
            raise InvalidDiaryEntryError("a diary entry needs some text")
        if len(stripped) > MAX_DIARY_ENTRY_LENGTH:
            raise InvalidDiaryEntryError(
                f"a diary entry has at most {MAX_DIARY_ENTRY_LENGTH} characters,"
                f" got {len(stripped)}"
            )
        object.__setattr__(self, "text", stripped)


@dataclass(frozen=True)
class DiaryDay:
    """One page of the diary: every entry of a day, the earliest first."""

    day: date
    entries: tuple[DiaryEntry, ...]


class Diary(Protocol):
    def write(self, entry: DiaryEntry) -> None:
        """Adds the entry to the page of its day. Raises DiaryStorageError."""
        ...

    def recent_days(self, limit: int) -> list[DiaryDay]:
        """The latest days with entries, the newest first. Raises DiaryStorageError."""
        ...
