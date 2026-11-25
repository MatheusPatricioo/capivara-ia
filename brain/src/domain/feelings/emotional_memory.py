from typing import Protocol

from src.domain.feelings.emotional_life import EmotionalSnapshot


class EmotionalMemoryError(Exception):
    """Raised when her emotional life cannot be read or written."""


class EmotionalMemory(Protocol):
    """Where her emotional life is kept between moments, restarts and processes."""

    def load(self) -> EmotionalSnapshot | None:
        """None when she has no emotional life yet (her first moment)."""
        ...

    def save(self, snapshot: EmotionalSnapshot) -> None: ...
