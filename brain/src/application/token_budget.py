import time
from collections import deque
from collections.abc import Callable

ONE_HOUR_IN_SECONDS = 3600.0


class HourlyTokenBudget:
    """Limits how many tokens the agent may spend in any sliding window of one hour.

    Each spending is kept with its time; spendings older than one hour stop counting.
    """

    def __init__(
        self, max_tokens_per_hour: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        if max_tokens_per_hour <= 0:
            raise ValueError(f"max_tokens_per_hour must be positive, got {max_tokens_per_hour}")
        self._max_tokens_per_hour = max_tokens_per_hour
        self._clock = clock
        self._spendings: deque[tuple[float, int]] = deque()

    def record(self, tokens: int) -> None:
        self._spendings.append((self._clock(), tokens))

    @property
    def tokens_used_in_the_last_hour(self) -> int:
        self._forget_old_spendings()
        return sum(tokens for _, tokens in self._spendings)

    def has_room(self) -> bool:
        return self.tokens_used_in_the_last_hour < self._max_tokens_per_hour

    def _forget_old_spendings(self) -> None:
        one_hour_ago = self._clock() - ONE_HOUR_IN_SECONDS
        while self._spendings and self._spendings[0][0] <= one_hour_ago:
            self._spendings.popleft()
