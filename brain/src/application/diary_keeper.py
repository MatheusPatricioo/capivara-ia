"""What she thought at the end of a free cycle goes into her diary, with how she felt."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.domain.diary import (
    Diary,
    DiaryEntry,
    DiaryMood,
    DiaryStorageError,
    InvalidDiaryEntryError,
)
from src.domain.feelings.emotion import EmotionalState

logger = logging.getLogger(__name__)


class DiaryKeeper:
    """Listens to the thoughts of the autonomous loop and writes each one in the diary.

    With feelings, each entry also records her mood at that moment (the mood meter).
    A thought that cannot be kept (empty, too long, disk error) is only logged: the diary
    never stops her from living the next cycle.
    """

    def __init__(
        self,
        diary: Diary,
        feelings: Callable[[], EmotionalState] | None = None,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._diary = diary
        self._feelings = feelings
        self._now = now

    def keep(self, thought: str) -> None:
        mood = DiaryMood.of(self._feelings()) if self._feelings is not None else None
        try:
            self._diary.write(DiaryEntry(self._now(), thought, mood))
        except (InvalidDiaryEntryError, DiaryStorageError) as error:
            logger.warning("Could not keep the thought in her diary: %s", error)
