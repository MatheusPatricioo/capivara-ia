"""The sky reaches the world over a real WebSocket. The forecast is fixed: no internet."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from websockets.sync.client import connect

from src.application.world_sky import WorldSky
from src.domain.weather import Sky
from src.domain.world_clock import ClockMode, WorldClock
from src.infrastructure.fixed_weather import FixedWeatherForecast
from src.infrastructure.sky_broadcaster import SkyBroadcaster
from src.infrastructure.world_server import WorldServer

LOCAL_HOST = "127.0.0.1"
ANY_FREE_PORT = 0
WAIT_TIMEOUT_SECONDS = 2.0
ONE_HOUR = 3600.0


@pytest.fixture
def server() -> Iterator[WorldServer]:
    with WorldServer(LOCAL_HOST, ANY_FREE_PORT) as world_server:
        yield world_server


@pytest.fixture
def rainy_fast_noon() -> WorldSky:
    clock = WorldClock(
        ClockMode.FAST, ONE_HOUR, now=lambda: datetime(2026, 11, 25, 10, 30, tzinfo=UTC)
    )
    return WorldSky(clock, FixedWeatherForecast(Sky.RAIN), weather_refresh_seconds=900.0)


def test_a_world_that_connects_later_gets_the_sky_right_away(
    server: WorldServer, rainy_fast_noon: WorldSky
) -> None:
    with (
        SkyBroadcaster(rainy_fast_noon, server, interval_seconds=60.0),
        connect(f"ws://{LOCAL_HOST}:{server.port}") as world,
    ):
        message = json.loads(world.recv(timeout=WAIT_TIMEOUT_SECONDS))

    assert message == {
        "type": "sky",
        "day_fraction": 0.5,
        "day_length_seconds": ONE_HOUR,
        "weather": "rain",
        "moon_phase": 0.5256,
    }
