from collections.abc import Callable

from src.domain.letter import Letter, LetterStorageError, Reply, SavedLetter


class InMemoryMailbox:
    """Keeps the letters in a list instead of Markdown files."""

    def __init__(self, letters: list[Letter] | None = None) -> None:
        self._saved: list[SavedLetter] = []
        for letter in letters or []:
            self.post(letter)

    @property
    def posted(self) -> list[Letter]:
        return [saved.letter for saved in self._saved]

    def post(self, letter: Letter) -> str:
        file_name = f"carta-{len(self._saved) + 1}.md"
        self._saved.append(SavedLetter(file_name, letter))
        return file_name

    def saved_letters(self) -> list[SavedLetter]:
        return list(self._saved)

    def mark_read(self, file_name: str) -> SavedLetter:
        return self._change(file_name, Letter.opened)

    def answer(self, file_name: str, reply: Reply) -> SavedLetter:
        return self._change(file_name, lambda letter: letter.answered(reply))

    def mark_reply_seen(self, file_name: str) -> SavedLetter:
        return self._change(file_name, Letter.reply_seen)

    def _change(self, file_name: str, change: Callable[[Letter], Letter]) -> SavedLetter:
        for index, saved in enumerate(self._saved):
            if saved.file_name == file_name:
                self._saved[index] = SavedLetter(file_name, change(saved.letter))
                return self._saved[index]
        raise LetterStorageError(f"no letter named {file_name}")


class BrokenMailbox:
    """A mailbox on a disk that fails."""

    def post(self, letter: Letter) -> str:
        raise LetterStorageError("disk is full")

    def saved_letters(self) -> list[SavedLetter]:
        return []

    def mark_read(self, file_name: str) -> SavedLetter:
        raise LetterStorageError("disk is full")

    def answer(self, file_name: str, reply: Reply) -> SavedLetter:
        raise LetterStorageError("disk is full")

    def mark_reply_seen(self, file_name: str) -> SavedLetter:
        raise LetterStorageError("disk is full")
