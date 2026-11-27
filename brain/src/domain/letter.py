"""Letters she writes to her creator while he is away, left in the mailbox of her world."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Protocol

MAX_LETTER_LENGTH = 1500
SECONDS_PER_HOUR = 3600.0


class InvalidLetterError(ValueError):
    """Raised when a letter or a reply breaks a rule (empty, too long, answered twice)."""


class LetterStorageError(Exception):
    """Raised when the mailbox cannot be read or written."""


class LetterStatus(StrEnum):
    UNREAD = "unread"
    """Waiting in the mailbox: her creator has not opened it yet."""
    READ = "read"


def _checked_text(text: str, what: str) -> str:
    """The text without spaces around it. Raises InvalidLetterError when empty or too long."""
    stripped = text.strip()
    if not stripped:
        raise InvalidLetterError(f"a {what} needs some text")
    if len(stripped) > MAX_LETTER_LENGTH:
        raise InvalidLetterError(
            f"a {what} has at most {MAX_LETTER_LENGTH} characters, got {len(stripped)}"
        )
    return stripped


@dataclass(frozen=True)
class Reply:
    """What her creator wrote back to one of her letters."""

    written_at: datetime
    text: str
    seen_by_her: bool = False
    """She read it in a cycle of her own, so it does not move her a second time."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _checked_text(self.text, "reply"))


@dataclass(frozen=True)
class Letter:
    written_at: datetime
    text: str
    status: LetterStatus = LetterStatus.UNREAD
    reply: Reply | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _checked_text(self.text, "letter"))

    @property
    def is_unread(self) -> bool:
        return self.status is LetterStatus.UNREAD

    def opened(self) -> "Letter":
        """The same letter, now read."""
        return replace(self, status=LetterStatus.READ)

    def answered(self, reply: Reply) -> "Letter":
        """The same letter with her creator's reply (answering it also means he read it).

        Each letter gets one reply: answering again raises InvalidLetterError.
        """
        if self.reply is not None:
            raise InvalidLetterError("this letter was already answered")
        return replace(self, status=LetterStatus.READ, reply=reply)

    @property
    def has_a_new_reply(self) -> bool:
        """Her creator answered and she has not read the answer yet."""
        return self.reply is not None and not self.reply.seen_by_her

    def reply_seen(self) -> "Letter":
        """The same letter, with the reply now read by her. Raises InvalidLetterError
        when there is no reply to read."""
        if self.reply is None:
            raise InvalidLetterError("this letter has no reply to read")
        return replace(self, reply=replace(self.reply, seen_by_her=True))


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

    def answer(self, file_name: str, reply: Reply) -> SavedLetter:
        """Keeps her creator's reply with the letter.

        Raises LetterStorageError when there is no such letter and InvalidLetterError when
        it was already answered.
        """
        ...

    def mark_reply_seen(self, file_name: str) -> SavedLetter:
        """Remembers she read the reply. Raises LetterStorageError when there is no such
        letter and InvalidLetterError when it has no reply."""
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
