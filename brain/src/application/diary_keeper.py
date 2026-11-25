"""What she thought at the end of a free cycle goes into her diary."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.domain.diary import Diary, DiaryEntry, DiaryStorageError, InvalidDiaryEntryError

logger = logging.getLogger(__name__)


class DiaryKeeper:
    """Listens to the thoughts of the autonomous loop and writes each one in the diary.

    A thought that cannot be kept (empty, too long, disk error) is only logged: the diary
    never stops her from living the next cycle.
    """

    def __init__(self, diary: Diary, now: Callable[[], datetime] = datetime.now) -> None:
        self._diary = diary
        self._now = now

    def keep(self, thought: str) -> None:
        try:
            self._diary.write(DiaryEntry(self._now(), thought))
        except (InvalidDiaryEntryError, DiaryStorageError) as error:
            logger.warning("Could not keep the thought in her diary: %s", error)
