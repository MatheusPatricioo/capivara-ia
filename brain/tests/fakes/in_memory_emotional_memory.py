from src.domain.feelings.emotional_life import EmotionalSnapshot
from src.domain.feelings.emotional_memory import EmotionalMemoryError


class InMemoryEmotionalMemory:
    """EmotionalMemory kept in a variable; share one between two hearts like two processes."""

    def __init__(self) -> None:
        self.snapshot: EmotionalSnapshot | None = None
        self.saves = 0

    def load(self) -> EmotionalSnapshot | None:
        return self.snapshot

    def save(self, snapshot: EmotionalSnapshot) -> None:
        self.snapshot = snapshot
        self.saves += 1


class BrokenEmotionalMemory:
    """A memory whose disk always fails."""

    def load(self) -> EmotionalSnapshot | None:
        raise EmotionalMemoryError("disk is gone")

    def save(self, snapshot: EmotionalSnapshot) -> None:
        raise EmotionalMemoryError("disk is gone")


class RecordingFeeler:
    """Remembers every event it was asked to feel."""

    def __init__(self) -> None:
        self.felt: list[object] = []

    def feel(self, event: object) -> None:
        self.felt.append(event)
