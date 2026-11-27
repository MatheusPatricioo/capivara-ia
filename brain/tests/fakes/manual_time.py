from collections.abc import Callable


class ManualTime:
    """A clock that only moves when something sleeps on it, so waits take no real time.

    during_sleep runs once, at the end of the first sleep: a way to make something
    happen "while" the code waits, like a new message from her creator.
    """

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
        self._during_sleep: Callable[[], None] | None = None

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
        if self._during_sleep is not None:
            happen, self._during_sleep = self._during_sleep, None
            happen()

    def while_sleeping(self, happen: Callable[[], None]) -> None:
        self._during_sleep = happen
