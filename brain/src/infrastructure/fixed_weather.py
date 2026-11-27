from src.domain.weather import Sky, Weather

FIXED_TEMPERATURE_CELSIUS = 20.0


class FixedWeatherForecast:
    """Always the same sky, set with WEATHER_OVERRIDE, to test rain without waiting for it."""

    def __init__(self, sky: Sky) -> None:
        self._sky = sky

    def current(self) -> Weather:
        return Weather(self._sky, FIXED_TEMPERATURE_CELSIUS)
