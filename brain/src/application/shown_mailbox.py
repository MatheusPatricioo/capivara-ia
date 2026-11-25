import logging
import threading
from typing import Protocol

from src.domain.letter import Letter, LetterStorageError, Mailbox, SavedLetter

logger = logging.getLogger(__name__)


class MailboxDisplay(Protocol):
    def show_mailbox(self, letters: list[SavedLetter]) -> None: ...


class ShownMailbox:
    """Decorator: a mailbox whose every change is shown in the world right away.

    A new letter raises the flag of the mailbox; a letter opened by Matheus lowers it.
    Letters are posted from the agent loop and opened from the world server thread, so a
    lock keeps the two from touching the files at the same time.
    """

    def __init__(self, mailbox: Mailbox, display: MailboxDisplay) -> None:
        self._mailbox = mailbox
        self._display = display
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

    def show(self) -> None:
        with self._lock:
            self._display.show_mailbox(self._mailbox.saved_letters())

    def open_letter(self, file_name: str) -> None:
        """Matheus opened a letter in the world. An unknown letter is only logged."""
        try:
            self.mark_read(file_name)
        except LetterStorageError as error:
            logger.warning("Could not mark the letter as read: %s", error)
            return
        logger.info("Matheus read the letter %s", file_name)
