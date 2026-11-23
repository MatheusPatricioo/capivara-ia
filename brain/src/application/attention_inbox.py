import threading
import time
from collections.abc import Callable

from src.domain.attention import Attention, PointOfAttention


class AttentionInbox:
    """Thread-safe door to the capybara's attention.

    The world server calls notice from its own thread whenever she walks by something,
    while the autonomous loop reads and lets go from the main thread. One lock keeps
    both sides from changing the attention at the same time.
    """

    def __init__(self, attention: Attention, clock: Callable[[], float] = time.monotonic) -> None:
        self._attention = attention
        self._clock = clock
        self._lock = threading.Lock()

    def notice(self, thing_id: str, description: str) -> bool:
        """Returns True when the thing became a new point of attention."""
        with self._lock:
            return self._attention.notice(thing_id, description, self._clock())

    def pending(self) -> tuple[PointOfAttention, ...]:
        with self._lock:
            return self._attention.pending

    def let_go(self, thing_id: str) -> None:
        with self._lock:
            self._attention.let_go(thing_id, self._clock())
