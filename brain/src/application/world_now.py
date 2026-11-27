from collections.abc import Callable
from datetime import time

from src.application.world_sky import SkyView
from src.domain.weather import Sky, Weather

TIME_PLACEHOLDER = "{time}"
PERIOD_PLACEHOLDER = "{period}"
WEATHER_PLACEHOLDER = "{weather}"

SKY_NAMES = {
    Sky.CLEAR: "céu limpo",
    Sky.CLOUDY: "nublado",
    Sky.FOG: "neblina",
    Sky.RAIN: "chovendo",
    Sky.STORM: "tempestade",
}
# Where each part of the day starts, latest first: the first start not after the time wins.
PERIOD_STARTS = (
    (time(18, 0), "de noite"),
    (time(12, 0), "de tarde"),
    (time(6, 0), "de manhã"),
    (time(0, 0), "de madrugada"),
)


class WorldNow:
    """What she sees around her right now: the time of day and the weather of her world.

    Without it she only knew what she remembered, so at night she said she wished to see
    the night sky. Read on every call: the time changes while she thinks and talks.
    """

    def __init__(self, look: Callable[[], SkyView], template: str) -> None:
        self._look = look
        self._template = template

    def compose(self) -> str:
        view = self._look()
        time_of_day = view.world_time.time_of_day
        return (
            self._template.replace(TIME_PLACEHOLDER, f"{time_of_day:%H:%M}")
            .replace(PERIOD_PLACEHOLDER, day_period(time_of_day))
            .replace(WEATHER_PLACEHOLDER, _weather_part(view.weather))
            .strip()
        )


def day_period(time_of_day: time) -> str:
    return next(name for start, name in PERIOD_STARTS if time_of_day >= start)


def _weather_part(weather: Weather | None) -> str:
    """Left out while the weather was never read: better silent than a made-up sky."""
    if weather is None:
        return ""
    return f", {SKY_NAMES[weather.sky]}, {weather.temperature_celsius:.0f} °C"
