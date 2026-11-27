"""The weather outside, which her world copies: when it rains in the real city, it rains there."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Sky(StrEnum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    FOG = "fog"
    RAIN = "rain"
    STORM = "storm"


RAINY_SKIES = frozenset({Sky.RAIN, Sky.STORM})


@dataclass(frozen=True)
class Weather:
    sky: Sky
    temperature_celsius: float

    @property
    def is_raining(self) -> bool:
        return self.sky in RAINY_SKIES


class WeatherUnavailableError(Exception):
    """The forecast could not be read (no internet, service down, odd answer)."""


class WeatherForecast(Protocol):
    def current(self) -> Weather:
        """The weather right now. Raises WeatherUnavailableError when it cannot be read."""
        ...
