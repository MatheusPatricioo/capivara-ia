"""What the sky of her world looks like now: the time of day and the weather."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from src.domain.moon import moon_phase
from src.domain.weather import Weather, WeatherForecast, WeatherUnavailableError
from src.domain.world_clock import WorldClock, WorldTime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkyView:
    world_time: WorldTime
    day_length_seconds: float
    """Real seconds in a whole world day, so the world can move the sun on its own."""
    weather: Weather | None
    """None while the weather was never read (or is switched off)."""
    moon_phase: float
    """From 0 (new moon) through 0.5 (full) to just under 1, by the real date."""


class WorldSky:
    """Looks at the clock every time, but asks the forecast only once per refresh period.

    The weather changes slowly and the forecast is a call over the internet. When a new
    reading fails, the last weather stays: a short outage should not stop the rain.
    """

    def __init__(
        self,
        clock: WorldClock,
        forecast: WeatherForecast | None,
        weather_refresh_seconds: float,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clock = clock
        self._forecast = forecast
        self._weather_refresh_seconds = weather_refresh_seconds
        self._monotonic = monotonic
        self._weather: Weather | None = None
        self._weather_checked_at: float | None = None

    def look(self) -> SkyView:
        return SkyView(
            self._clock.now(),
            self._clock.day_length_seconds,
            self._current_weather(),
            moon_phase(self._clock.real_moment()),
        )

    def _current_weather(self) -> Weather | None:
        if self._forecast is not None and self._is_time_to_check_the_weather():
            self._weather_checked_at = self._monotonic()
            try:
                self._weather = self._forecast.current()
            except WeatherUnavailableError as error:
                logger.warning("Weather unavailable, keeping the last one: %s", error)
        return self._weather

    def _is_time_to_check_the_weather(self) -> bool:
        if self._weather_checked_at is None:
            return True
        elapsed = self._monotonic() - self._weather_checked_at
        return elapsed >= self._weather_refresh_seconds
