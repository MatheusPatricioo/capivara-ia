from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class PointOfAttention:
    """Something that caught the capybara's eye in her world."""

    thing_id: str
    description: str


class Attention:
    """Things that caught the capybara's eye and are waiting for her to think about them.

    - A thing already waiting is not added twice.
    - After she lets a thing go (she researched it or decided it was not worth it), it
      cannot catch her eye again for rest_seconds.
    - Only the capacity most recent things wait; when full, the oldest one is forgotten.

    Times are seconds from any steady clock; the caller passes them, so the rules stay pure.
    """

    def __init__(self, capacity: int, rest_seconds: float) -> None:
        if capacity <= 0:
            raise ValueError(f"attention capacity must be positive, got {capacity}")
        if rest_seconds < 0:
            raise ValueError(f"rest_seconds cannot be negative, got {rest_seconds}")
        self._capacity = capacity
        self._rest_seconds = rest_seconds
        self._waiting: OrderedDict[str, PointOfAttention] = OrderedDict()
        self._let_go_at: dict[str, float] = {}

    @property
    def pending(self) -> tuple[PointOfAttention, ...]:
        """What is waiting for her, from the most recent to the oldest."""
        return tuple(reversed(self._waiting.values()))

    def notice(self, thing_id: str, description: str, now: float) -> bool:
        """Returns True when the thing became a new point of attention."""
        if thing_id in self._waiting or self._is_resting(thing_id, now):
            return False
        self._waiting[thing_id] = PointOfAttention(thing_id, description)
        if len(self._waiting) > self._capacity:
            self._waiting.popitem(last=False)
        return True

    def let_go(self, thing_id: str, now: float) -> None:
        """She is done with this thing for now: it leaves the list and starts resting."""
        self._waiting.pop(thing_id, None)
        self._let_go_at[thing_id] = now

    def _is_resting(self, thing_id: str, now: float) -> bool:
        let_go_at = self._let_go_at.get(thing_id)
        return let_go_at is not None and now - let_go_at < self._rest_seconds
