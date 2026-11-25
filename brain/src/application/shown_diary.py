"""Her diary, shown in the world: every new entry appears on the diary desk right away."""

import logging
from typing import Protocol

from src.domain.diary import Diary, DiaryDay, DiaryEntry, DiaryStorageError

logger = logging.getLogger(__name__)

DEFAULT_SHOWN_DAYS = 14


class DiaryDisplay(Protocol):
    def show_diary(self, days: list[DiaryDay]) -> None: ...


class ShownDiary:
    """Decorator: a diary whose latest days are shown in the world after every entry.

    Only the latest days travel to the world, so the message stays small; the older pages
    are still in the folder.
    """

    def __init__(
        self, diary: Diary, display: DiaryDisplay, shown_days: int = DEFAULT_SHOWN_DAYS
    ) -> None:
        self._diary = diary
        self._display = display
        self._shown_days = shown_days

    def write(self, entry: DiaryEntry) -> None:
        self._diary.write(entry)
        self.show()

    def recent_days(self, limit: int) -> list[DiaryDay]:
        return self._diary.recent_days(limit)

    def show(self) -> None:
        """A diary that cannot be read is only logged: the world keeps what it had."""
        try:
            days = self._diary.recent_days(self._shown_days)
        except DiaryStorageError as error:
            logger.warning("Could not read her diary to show it: %s", error)
            return
        self._display.show_diary(days)
