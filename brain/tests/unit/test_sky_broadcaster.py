from datetime import datetime, time

import pytest

from src.application.world_sky import SkyView, WorldSky
from src.domain.weather import Sky, Weather
from src.domain.world_clock import ClockMode, WorldClock, WorldTime
from src.infrastructure.fixed_weather import FixedWeatherForecast
from src.infrastructure.sky_broadcaster import SkyBroadcaster
from src.infrastructure.world_messages import SkyMessage, WorldMessage, sky_message

ONE_HOUR = 3600.0


class RecordingBroadcaster:
    def __init__(self) -> None:
        self.sent: list[tuple[WorldMessage, bool]] = []

    def broadcast(self, message: WorldMessage, remember: bool = False) -> None:
        self.sent.append((message, remember))


@pytest.fixture
def broadcaster() -> RecordingBroadcaster:
    return RecordingBroadcaster()


@pytest.fixture
def rainy_noon() -> WorldSky:
    clock = WorldClock(ClockMode.FAST, ONE_HOUR, now=lambda: datetime(2026, 11, 25, 10, 30))
    return WorldSky(clock, FixedWeatherForecast(Sky.RAIN), weather_refresh_seconds=900.0)


def test_sky_message_carries_the_time_the_day_length_and_the_weather() -> None:
    view = SkyView(WorldTime(time(12, 0)), ONE_HOUR, Weather(Sky.RAIN, 19.0))

    assert sky_message(view) == SkyMessage(
        day_fraction=0.5, day_length_seconds=ONE_HOUR, weather="rain"
    )


def test_sky_message_says_unknown_when_the_weather_was_never_read() -> None:
    view = SkyView(WorldTime(time(12, 0)), ONE_HOUR, None)

    assert sky_message(view).weather == "unknown"


def test_a_moment_just_before_midnight_is_sent_as_midnight() -> None:
    view = SkyView(WorldTime(time(23, 59, 59, 999999)), ONE_HOUR, None)

    assert sky_message(view).day_fraction == 0.0


def test_publish_sends_a_remembered_sky_message(
    rainy_noon: WorldSky, broadcaster: RecordingBroadcaster
) -> None:
    SkyBroadcaster(rainy_noon, broadcaster, interval_seconds=10.0).publish()

    assert broadcaster.sent == [
        (SkyMessage(day_fraction=0.5, day_length_seconds=ONE_HOUR, weather="rain"), True)
    ]


def test_starting_publishes_right_away(
    rainy_noon: WorldSky, broadcaster: RecordingBroadcaster
) -> None:
    with SkyBroadcaster(rainy_noon, broadcaster, interval_seconds=60.0):
        pass

    assert len(broadcaster.sent) == 1


def test_fixed_weather_always_has_the_chosen_sky() -> None:
    assert FixedWeatherForecast(Sky.STORM).current().sky is Sky.STORM
