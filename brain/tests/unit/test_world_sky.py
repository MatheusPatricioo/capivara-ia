from datetime import UTC, datetime, time

import pytest

from src.application.world_sky import WorldSky
from src.domain.weather import Sky, Weather, WeatherUnavailableError
from src.domain.world_clock import ClockMode, WorldClock

REFRESH_SECONDS = 900.0
RAIN = Weather(Sky.RAIN, 19.0)
SUN = Weather(Sky.CLEAR, 27.0)


class ScriptedForecast:
    """Answers each reading with the next item: a weather, or None for a failed reading."""

    def __init__(self, *readings: Weather | None) -> None:
        self._readings = list(readings)
        self.calls = 0

    def current(self) -> Weather:
        reading = self._readings[min(self.calls, len(self._readings) - 1)]
        self.calls += 1
        if reading is None:
            raise WeatherUnavailableError("offline")
        return reading


class ManualTimer:
    def __init__(self) -> None:
        self.seconds = 0.0

    def __call__(self) -> float:
        return self.seconds


@pytest.fixture
def clock() -> WorldClock:
    return WorldClock(
        ClockMode.FAST, 3600.0, now=lambda: datetime(2026, 11, 25, 10, 30, tzinfo=UTC)
    )


@pytest.fixture
def timer() -> ManualTimer:
    return ManualTimer()


def sky_with(clock: WorldClock, timer: ManualTimer, forecast: ScriptedForecast) -> WorldSky:
    return WorldSky(clock, forecast, REFRESH_SECONDS, monotonic=timer)


def test_shows_the_world_time(clock: WorldClock, timer: ManualTimer) -> None:
    sky = sky_with(clock, timer, ScriptedForecast(RAIN))

    assert sky.look().world_time.time_of_day == time(12, 0)


def test_tells_how_long_a_world_day_lasts(clock: WorldClock, timer: ManualTimer) -> None:
    sky = sky_with(clock, timer, ScriptedForecast(RAIN))

    assert sky.look().day_length_seconds == 3600.0


def test_shows_the_weather_from_the_forecast(clock: WorldClock, timer: ManualTimer) -> None:
    sky = sky_with(clock, timer, ScriptedForecast(RAIN))

    assert sky.look().weather == RAIN


def test_without_a_forecast_there_is_no_weather(clock: WorldClock) -> None:
    sky = WorldSky(clock, None, REFRESH_SECONDS)

    assert sky.look().weather is None


def test_asks_the_forecast_once_within_the_refresh_period(
    clock: WorldClock, timer: ManualTimer
) -> None:
    forecast = ScriptedForecast(RAIN)
    sky = sky_with(clock, timer, forecast)

    sky.look()
    timer.seconds = REFRESH_SECONDS - 1
    sky.look()

    assert forecast.calls == 1


def test_reads_the_new_weather_after_the_refresh_period(
    clock: WorldClock, timer: ManualTimer
) -> None:
    sky = sky_with(clock, timer, ScriptedForecast(RAIN, SUN))

    sky.look()
    timer.seconds = REFRESH_SECONDS
    assert sky.look().weather == SUN


def test_keeps_the_last_weather_when_a_reading_fails(clock: WorldClock, timer: ManualTimer) -> None:
    sky = sky_with(clock, timer, ScriptedForecast(RAIN, None))

    sky.look()
    timer.seconds = REFRESH_SECONDS
    assert sky.look().weather == RAIN


def test_has_no_weather_when_the_first_reading_fails(clock: WorldClock, timer: ManualTimer) -> None:
    sky = sky_with(clock, timer, ScriptedForecast(None))

    assert sky.look().weather is None


def test_shows_the_moon_phase_of_the_real_date(clock: WorldClock, timer: ManualTimer) -> None:
    sky = sky_with(clock, timer, ScriptedForecast(RAIN))

    # 25 Nov 2026 is the day after a full moon.
    assert sky.look().moon_phase == pytest.approx(0.53, abs=0.01)
