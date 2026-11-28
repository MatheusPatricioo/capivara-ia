from datetime import time

import pytest

from src.application.world_now import WorldNow, day_period
from src.application.world_sky import SkyView
from src.domain.weather import Sky, Weather
from src.domain.world_clock import WorldTime

TEMPLATE = "(Agora: {time}, {period}{weather}.)"
DAY_LENGTH_SECONDS = 86400.0


def world_now_at(time_of_day: time, weather: Weather | None) -> WorldNow:
    view = SkyView(WorldTime(time_of_day), DAY_LENGTH_SECONDS, weather, 0.5)
    return WorldNow(lambda: view, TEMPLATE)


@pytest.mark.parametrize(
    ("time_of_day", "period"),
    [
        (time(2, 0), "de madrugada"),
        (time(6, 0), "de manhã"),
        (time(12, 0), "de tarde"),
        (time(17, 59), "de tarde"),
        (time(18, 0), "de noite"),
        (time(23, 59), "de noite"),
    ],
)
def test_names_the_part_of_the_day(time_of_day: time, period: str) -> None:
    assert day_period(time_of_day) == period


def test_tells_the_time_the_part_of_the_day_and_the_weather() -> None:
    world_now = world_now_at(time(21, 30), Weather(Sky.CLEAR, 18.4))

    assert world_now.compose() == "(Agora: 21:30, de noite, céu limpo, 18 °C.)"


def test_leaves_the_weather_out_while_it_was_never_read() -> None:
    world_now = world_now_at(time(9, 5), None)

    assert world_now.compose() == "(Agora: 09:05, de manhã.)"


def test_looks_at_the_sky_again_on_every_call() -> None:
    views = iter(
        [
            SkyView(WorldTime(time(17, 0)), DAY_LENGTH_SECONDS, None, 0.5),
            SkyView(WorldTime(time(19, 0)), DAY_LENGTH_SECONDS, None, 0.5),
        ]
    )
    world_now = WorldNow(lambda: next(views), TEMPLATE)
    world_now.compose()

    assert world_now.compose() == "(Agora: 19:00, de noite.)"
