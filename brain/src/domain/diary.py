"""Her personal diary: at the end of each free cycle, she writes what she thought or did,
and how she felt while writing it."""

from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean
from typing import Protocol

from src.domain.feelings.emotion import Emotion, EmotionalState

MAX_DIARY_ENTRY_LENGTH = 2000
FELT_MIN_INTENSITY = 0.2
"""Weaker emotions are not worth writing down: below it, she was simply calm."""


class InvalidDiaryEntryError(ValueError):
    """Raised when an entry breaks a rule (empty, too long, a mood out of range)."""


class DiaryStorageError(Exception):
    """Raised when the diary cannot be read or written."""


@dataclass(frozen=True)
class DiaryMood:
    """How she felt when she wrote an entry: her strongest emotion (None when calm) and how
    good she felt overall, from -1 (all bad) to 1 (all good)."""

    emotion: Emotion | None
    valence: float

    def __post_init__(self) -> None:
        if not -1.0 <= self.valence <= 1.0:
            raise InvalidDiaryEntryError(f"a mood valence is between -1 and 1, got {self.valence}")

    @classmethod
    def of(cls, emotions: EmotionalState) -> "DiaryMood":
        strongest = emotions.strongest(limit=1, minimum=FELT_MIN_INTENSITY)
        emotion = strongest[0][0] if strongest else None
        return cls(emotion, round(emotions.valence, 2))


@dataclass(frozen=True)
class DiaryEntry:
    written_at: datetime
    text: str
    mood: DiaryMood | None = None
    """None for entries written without feelings (or before the mood meter existed)."""

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

    @property
    def average_valence(self) -> float | None:
        """How good the day felt on average, or None when no entry has a mood."""
        valences = [entry.mood.valence for entry in self.entries if entry.mood is not None]
        return mean(valences) if valences else None


class Diary(Protocol):
    def write(self, entry: DiaryEntry) -> None:
        """Adds the entry to the page of its day. Raises DiaryStorageError."""
        ...

    def recent_days(self, limit: int) -> list[DiaryDay]:
        """The latest days with entries, the newest first. Raises DiaryStorageError."""
        ...
