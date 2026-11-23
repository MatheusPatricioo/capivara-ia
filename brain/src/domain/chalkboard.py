from collections import deque

from src.domain.drawing import Drawing, InvalidDrawingError


class Chalkboard:
    """Keeps only the most recent drawings: when a new one arrives, the oldest is erased."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise InvalidDrawingError(f"chalkboard capacity must be positive, got {capacity}")
        self._drawings: deque[Drawing] = deque(maxlen=capacity)

    @property
    def drawings(self) -> tuple[Drawing, ...]:
        """Drawings currently on the board, from the oldest to the newest."""
        return tuple(self._drawings)

    def pin(self, drawing: Drawing) -> Drawing | None:
        """Pins the drawing and returns the one erased to make room, if any."""
        erased = self._drawings[0] if self._is_full() else None
        self._drawings.append(drawing)
        return erased

    def _is_full(self) -> bool:
        return len(self._drawings) == self._drawings.maxlen
