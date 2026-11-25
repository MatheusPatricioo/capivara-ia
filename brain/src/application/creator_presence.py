import threading
import time
from collections.abc import Callable

NEVER = float("-inf")


class CreatorPresence:
    """Whether her creator is talking with her now. Talking with him comes first: her own
    thoughts wait while the conversation lasts, and go on after quiet_seconds without a
    new exchange. Each message he sends, and each reply she gives, renews that time.

    Two threads use it: the chat marks the exchanges, the autonomous loop waits. A lock
    keeps the time of the last exchange consistent between them.
    """

    def __init__(
        self,
        quiet_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._quiet_seconds = quiet_seconds
        self._clock = clock
        self._sleep = sleep
        self._last_exchange_at = NEVER
        self._lock = threading.Lock()

    @property
    def quiet_seconds(self) -> float:
        return self._quiet_seconds

    def mark_exchange(self) -> None:
        """A message from him or a reply from her: the conversation goes on."""
        with self._lock:
            self._last_exchange_at = self._clock()

    def is_talking(self) -> bool:
        return self._seconds_until_quiet() > 0.0

    def wait_while_talking(self) -> None:
        """Returns at once when they are not talking; otherwise sleeps until the quiet
        time passes. A message that arrives during the sleep makes it sleep again."""
        while (seconds_left := self._seconds_until_quiet()) > 0.0:
            self._sleep(seconds_left)

    def _seconds_until_quiet(self) -> float:
        with self._lock:
            quiet_at = self._last_exchange_at + self._quiet_seconds
        return quiet_at - self._clock()
