import httpx
import pytest

from src.capybara_sky import build_weather_forecast
from src.domain.weather import Sky
from src.infrastructure.fixed_weather import FixedWeatherForecast
from src.infrastructure.open_meteo_weather import OpenMeteoWeather
from src.infrastructure.settings import Settings


@pytest.fixture
def client() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))


def test_the_real_forecast_is_used_by_default(client: httpx.Client) -> None:
    settings = Settings(_env_file=None, weather_enabled=True, weather_override=None)

    assert isinstance(build_weather_forecast(settings, client), OpenMeteoWeather)


def test_the_override_replaces_the_real_forecast(client: httpx.Client) -> None:
    settings = Settings(_env_file=None, weather_override=Sky.RAIN)

    assert isinstance(build_weather_forecast(settings, client), FixedWeatherForecast)


def test_no_forecast_when_the_weather_is_switched_off(client: httpx.Client) -> None:
    settings = Settings(_env_file=None, weather_enabled=False, weather_override=None)

    assert build_weather_forecast(settings, client) is None
