import threading
import time
from collections.abc import Callable

NEVER = float("-inf")


class CreatorPresence:
    """Whether her creator is talking with her now. Talking with him comes first: her own
    thoughts wait while the conversation lasts, and go on after quiet_seconds without a
    new exchange. Each message he sends, and each reply she gives, renews that time.

    He can also end it at once (end): then her thoughts go on right away, and a reply she
    was still thinking about no longer renews the conversation.

    Two threads use it: the chat marks the exchanges, the autonomous loop waits. A lock
    keeps the time of the last exchange consistent between them, and an Event wakes the
    waiting loop up when he ends the conversation.
    """

    def __init__(
        self,
        quiet_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._quiet_seconds = quiet_seconds
        self._clock = clock
        self._wake_up = threading.Event()
        self._sleep = sleep if sleep is not None else self._sleep_until_woken
        self._last_exchange_at = NEVER
        self._ended = False
        self._lock = threading.Lock()

    @property
    def quiet_seconds(self) -> float:
        return self._quiet_seconds

    def mark_exchange(self) -> None:
        """A message from him: the conversation goes on (or starts again after an end)."""
        with self._lock:
            self._last_exchange_at = self._clock()
            self._ended = False

    def mark_reply(self) -> bool:
        """A reply from her renews the conversation, unless he ended it meanwhile.
        Returns whether it was renewed."""
        with self._lock:
            if self._ended:
                return False
            self._last_exchange_at = self._clock()
            return True

    def end(self) -> None:
        """He said goodbye: the conversation is over now, without waiting the quiet time."""
        with self._lock:
            self._last_exchange_at = NEVER
            self._ended = True
        self._wake_up.set()

    def is_talking(self) -> bool:
        return self._seconds_until_quiet() > 0.0

    def wait_while_talking(self) -> None:
        """Returns at once when they are not talking; otherwise sleeps until the quiet
        time passes. A message that arrives during the sleep makes it sleep again."""
        while (seconds_left := self._seconds_until_quiet()) > 0.0:
            self._sleep(seconds_left)

    def _sleep_until_woken(self, seconds: float) -> None:
        """Like time.sleep, but end() wakes it up early."""
        self._wake_up.wait(seconds)
        self._wake_up.clear()

    def _seconds_until_quiet(self) -> float:
        with self._lock:
            quiet_at = self._last_exchange_at + self._quiet_seconds
        return quiet_at - self._clock()
