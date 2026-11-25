"""Letters she writes to Matheus while he is away, left in the mailbox of her world."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Protocol

MAX_LETTER_LENGTH = 1500
SECONDS_PER_HOUR = 3600.0


class InvalidLetterError(ValueError):
    """Raised when a letter breaks a rule (empty, too long)."""


class LetterStorageError(Exception):
    """Raised when the mailbox cannot be read or written."""


class LetterStatus(StrEnum):
    UNREAD = "unread"
    """Waiting in the mailbox: Matheus has not opened it yet."""
    READ = "read"


@dataclass(frozen=True)
class Letter:
    written_at: datetime
    text: str
    status: LetterStatus = LetterStatus.UNREAD

    def __post_init__(self) -> None:
        text = self.text.strip()
        if not text:
            raise InvalidLetterError("a letter needs some text")
        if len(text) > MAX_LETTER_LENGTH:
            raise InvalidLetterError(
                f"a letter has at most {MAX_LETTER_LENGTH} characters, got {len(text)}"
            )
        object.__setattr__(self, "text", text)

    @property
    def is_unread(self) -> bool:
        return self.status is LetterStatus.UNREAD

    def opened(self) -> "Letter":
        """The same letter, now read."""
        return replace(self, status=LetterStatus.READ)


@dataclass(frozen=True)
class SavedLetter:
    """A letter in the mailbox, with the file name that identifies it."""

    file_name: str
    letter: Letter


class Mailbox(Protocol):
    def post(self, letter: Letter) -> str:
        """Leaves the letter in the mailbox and returns its file name."""
        ...

    def saved_letters(self) -> list[SavedLetter]:
        """Every letter in the mailbox, the oldest first."""
        ...

    def mark_read(self, file_name: str) -> SavedLetter:
        """Marks the letter as read. Raises LetterStorageError when there is no such letter."""
        ...


@dataclass(frozen=True)
class LetterRhythm:
    """How often she may write: she misses him, but she does not flood his mailbox."""

    min_hours_between: float = 20.0
    """Hours since her last letter before she writes another one."""
    max_unread: int = 3
    """While this many letters wait unread, she stops writing and just waits."""

    def __post_init__(self) -> None:
        if self.min_hours_between < 0:
            raise ValueError(f"min_hours_between cannot be negative: {self.min_hours_between}")
        if self.max_unread <= 0:
            raise ValueError(f"max_unread must be positive, got {self.max_unread}")

    def allows_a_new_letter(self, letters: Sequence[Letter], now: datetime) -> bool:
        unread_count = sum(1 for letter in letters if letter.is_unread)
        if unread_count >= self.max_unread:
            return False
        if not letters:
            return True
        hours_since_last = (now - letters[-1].written_at).total_seconds() / SECONDS_PER_HOUR
        return hours_since_last >= self.min_hours_between
