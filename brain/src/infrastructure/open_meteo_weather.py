"""Current weather from Open-Meteo (https://open-meteo.com): free, no API key."""

import httpx
from pydantic import BaseModel, ValidationError

from src.domain.weather import Sky, Weather, WeatherUnavailableError

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes, as listed in the Open-Meteo docs.
CLEAR_CODES = frozenset({0, 1})
CLOUDY_CODES = frozenset({2, 3})
FOG_CODES = frozenset({45, 48})
STORM_CODES = frozenset({95, 96, 99})
# Everything else falls from the sky: drizzle (51-57), rain (61-67), snow (71-77),
# showers (80-86). Snow never happens in Belo Horizonte, so it simply counts as rain.


class _CurrentConditions(BaseModel):
    weather_code: int
    temperature_2m: float


class _ForecastResponse(BaseModel):
    current: _CurrentConditions


def sky_from_wmo_code(code: int) -> Sky:
    if code in CLEAR_CODES:
        return Sky.CLEAR
    if code in CLOUDY_CODES:
        return Sky.CLOUDY
    if code in FOG_CODES:
        return Sky.FOG
    if code in STORM_CODES:
        return Sky.STORM
    return Sky.RAIN


class OpenMeteoWeather:
    """Reads the weather right now at one place (latitude and longitude)."""

    def __init__(self, client: httpx.Client, latitude: float, longitude: float) -> None:
        self._client = client
        self._latitude = latitude
        self._longitude = longitude

    def current(self) -> Weather:
        try:
            response = self._client.get(
                OPEN_METEO_URL,
                params={
                    "latitude": self._latitude,
                    "longitude": self._longitude,
                    "current": "weather_code,temperature_2m",
                },
            )
            response.raise_for_status()
            conditions = _ForecastResponse.model_validate_json(response.content).current
        except httpx.HTTPError as error:
            raise WeatherUnavailableError(f"Could not reach Open-Meteo: {error}") from error
        except ValidationError as error:
            raise WeatherUnavailableError("Unexpected answer from Open-Meteo") from error
        return Weather(sky_from_wmo_code(conditions.weather_code), conditions.temperature_2m)
