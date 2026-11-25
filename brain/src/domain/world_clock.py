"""The time in her world: the real local time, or a fast day to test day and night quickly."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import StrEnum

SECONDS_PER_DAY = 24 * 60 * 60
SUNRISE = time(6, 0)
SUNSET = time(18, 0)
"""Fixed for now. Real sunrise and sunset can come later, from the weather forecast."""


class ClockMode(StrEnum):
    REAL = "real"
    """Her day follows the clock on the wall."""
    FAST = "fast"
    """A whole day fits in a short real time (one hour by default), for quick tests."""


class DayPhase(StrEnum):
    DAY = "day"
    NIGHT = "night"


@dataclass(frozen=True)
class WorldTime:
    """A moment of the day in her world."""

    time_of_day: time

    @property
    def phase(self) -> DayPhase:
        if SUNRISE <= self.time_of_day < SUNSET:
            return DayPhase.DAY
        return DayPhase.NIGHT

    @property
    def day_fraction(self) -> float:
        """From 0 (midnight) to just under 1 (the next midnight), e.g. 0.5 at noon."""
        return _seconds_since_midnight(self.time_of_day) / SECONDS_PER_DAY


class WorldClock:
    """Tells the time in her world.

    In fast mode, each real stretch of fast_day_seconds is a whole world day, counted from
    real midnight. With a one-hour day, every real hour starts at world midnight: the sun
    rises at minute 15, it is noon at minute 30 and night falls at minute 45.
    """

    def __init__(
        self,
        mode: ClockMode,
        fast_day_seconds: float,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        if fast_day_seconds <= 0:
            raise ValueError(f"fast_day_seconds must be positive, got {fast_day_seconds}")
        self._mode = mode
        self._fast_day_seconds = fast_day_seconds
        self._now = now

    @property
    def day_length_seconds(self) -> float:
        """How many real seconds a whole world day lasts."""
        if self._mode is ClockMode.REAL:
            return SECONDS_PER_DAY
        return self._fast_day_seconds

    def now(self) -> WorldTime:
        real_time = self._now().time()
        if self._mode is ClockMode.REAL:
            return WorldTime(real_time)
        return WorldTime(self._speed_up(real_time))

    def _speed_up(self, real_time: time) -> time:
        speed = SECONDS_PER_DAY / self._fast_day_seconds
        world_seconds = (_seconds_since_midnight(real_time) * speed) % SECONDS_PER_DAY
        return (datetime.min + timedelta(seconds=world_seconds)).time()


def _seconds_since_midnight(moment: time) -> float:
    return moment.hour * 3600 + moment.minute * 60 + moment.second + moment.microsecond / 1e6
