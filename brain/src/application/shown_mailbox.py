import logging
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from src.domain.letter import (
    InvalidLetterError,
    Letter,
    LetterStorageError,
    Mailbox,
    Reply,
    SavedLetter,
)

logger = logging.getLogger(__name__)


class MailboxDisplay(Protocol):
    def show_mailbox(self, letters: list[SavedLetter]) -> None: ...


class ShownMailbox:
    """Decorator: a mailbox whose every change is shown in the world right away.

    A new letter raises the flag of the mailbox; a letter opened by her creator lowers it, and
    his reply shows up under the letter.
    Letters are posted from the agent loop and opened from the world server thread, so a
    lock keeps the two from touching the files at the same time.
    """

    def __init__(
        self,
        mailbox: Mailbox,
        display: MailboxDisplay,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._mailbox = mailbox
        self._display = display
        self._now = now
        self._lock = threading.RLock()

    def post(self, letter: Letter) -> str:
        with self._lock:
            file_name = self._mailbox.post(letter)
            self.show()
            return file_name

    def saved_letters(self) -> list[SavedLetter]:
        with self._lock:
            return self._mailbox.saved_letters()

    def mark_read(self, file_name: str) -> SavedLetter:
        with self._lock:
            opened = self._mailbox.mark_read(file_name)
            self.show()
            return opened

    def answer(self, file_name: str, reply: Reply) -> SavedLetter:
        with self._lock:
            answered = self._mailbox.answer(file_name, reply)
            self.show()
            return answered

    def mark_reply_seen(self, file_name: str) -> SavedLetter:
        """She read the reply: nothing changes in the world, so nothing is shown."""
        with self._lock:
            return self._mailbox.mark_reply_seen(file_name)

    def mark_reply_felt(self, file_name: str) -> SavedLetter:
        """The reply moved her: nothing changes in the world, so nothing is shown."""
        with self._lock:
            return self._mailbox.mark_reply_felt(file_name)

    def reply_to_letter(self, file_name: str, text: str) -> None:
        """Her creator answered a letter in the world. A bad reply is only logged: the world
        keeps showing the letter without it, so he can try again."""
        try:
            self.answer(file_name, Reply(self._now(), text))
        except (InvalidLetterError, LetterStorageError) as error:
            logger.warning("Could not keep the reply to %s: %s", file_name, error)
            self.show()
            return
        logger.info("Her creator answered the letter %s", file_name)

    def show(self) -> None:
        with self._lock:
            self._display.show_mailbox(self._mailbox.saved_letters())

    def open_letter(self, file_name: str) -> None:
        """Her creator opened a letter in the world. An unknown letter is only logged."""
        try:
            self.mark_read(file_name)
        except LetterStorageError as error:
            logger.warning("Could not mark the letter as read: %s", error)
            return
        logger.info("Her creator read the letter %s", file_name)
