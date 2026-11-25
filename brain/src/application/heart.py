import logging
import random
import threading
import time
from collections.abc import Callable

from src.domain.feelings.appraisal import EmotionalEvent
from src.domain.feelings.emotional_life import EmotionalLife, EmotionalSnapshot
from src.domain.feelings.emotional_memory import EmotionalMemory, EmotionalMemoryError
from src.domain.feelings.needs import NeedRhythm
from src.domain.feelings.temperament import Temperament

logger = logging.getLogger(__name__)


def _ignore_change(life: EmotionalLife) -> None:
    pass


class Heart:
    """The door to her emotional life, for every part of the brain.

    Every call reads the saved life, lives through the time since then, applies what
    happened and saves it again. That is how the chat (another process) and the live
    capybara share one emotional life. One lock keeps the world server thread and the
    loop thread from changing it at the same time.

    When the memory fails, she keeps feeling with the last life she had in hand: a broken
    file must never stop her.
    """

    def __init__(
        self,
        memory: EmotionalMemory,
        temperament: Temperament | None = None,
        rhythm: NeedRhythm | None = None,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._memory = memory
        self._temperament = temperament or Temperament()
        self._rhythm = rhythm or NeedRhythm()
        self._rng = rng or random.Random()
        self._clock = clock
        self._on_change: Callable[[EmotionalLife], None] = _ignore_change
        self._lock = threading.Lock()
        self._last_snapshot: EmotionalSnapshot | None = None

    def watch(self, on_change: Callable[[EmotionalLife], None]) -> None:
        """on_change runs after every change, like showing her feelings in the world.

        Set after creation because the world (the body) is built after the heart.
        """
        self._on_change = on_change

    def feel(self, event: EmotionalEvent) -> EmotionalLife:
        with self._lock:
            life = self._open()
            life.experience(event, self._clock())
            logger.info("She felt %s: %s", event.kind.value, _describe(life))
            return self._close(life)

    def check_in(self, pending_wishes: int | None = None) -> EmotionalLife:
        """Lives through the time since the last moment; returns how she is now."""
        with self._lock:
            life = self._open()
            if pending_wishes is not None:
                life.notice_pending_wishes(pending_wishes)
            life.advance(self._clock())
            return self._close(life)

    def _open(self) -> EmotionalLife:
        snapshot = self._load() or self._last_snapshot
        if snapshot is None:
            logger.info("Her emotional life begins")
            snapshot = EmotionalLife.newborn(self._clock(), self._temperament)
        return EmotionalLife(snapshot, self._temperament, self._rhythm, rng=self._rng)

    def _close(self, life: EmotionalLife) -> EmotionalLife:
        self._last_snapshot = life.snapshot()
        try:
            self._memory.save(self._last_snapshot)
        except EmotionalMemoryError as error:
            logger.warning("Could not save her emotional life: %s", error)
        try:
            self._on_change(life)
        except Exception:
            # Showing her feelings must never break feeling them.
            logger.exception("Failed to show her feelings")
        return life

    def _load(self) -> EmotionalSnapshot | None:
        try:
            return self._memory.load()
        except EmotionalMemoryError as error:
            logger.warning("Could not read her emotional life: %s", error)
            return None


def _describe(life: EmotionalLife) -> str:
    return ", ".join(
        f"{emotion.value} {intensity:.2f}" for emotion, intensity in life.emotions.strongest(3)
    )
