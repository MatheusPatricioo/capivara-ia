import httpx
import pytest

from src.domain.weather import Sky, Weather, WeatherUnavailableError
from src.infrastructure.open_meteo_weather import OpenMeteoWeather, sky_from_wmo_code

BELO_HORIZONTE_LATITUDE = -19.9167
BELO_HORIZONTE_LONGITUDE = -43.9345
MODERATE_RAIN_CODE = 63


class RecordingTransport(httpx.BaseTransport):
    """Fake Open-Meteo: always moderate rain at 19.5 °C, and records the requests."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        current = {"weather_code": MODERATE_RAIN_CODE, "temperature_2m": 19.5}
        return httpx.Response(200, json={"current": current})


@pytest.fixture
def transport() -> RecordingTransport:
    return RecordingTransport()


@pytest.fixture
def forecast(transport: RecordingTransport) -> OpenMeteoWeather:
    client = httpx.Client(transport=transport)
    return OpenMeteoWeather(client, BELO_HORIZONTE_LATITUDE, BELO_HORIZONTE_LONGITUDE)


def answering(status_code: int, body: object) -> OpenMeteoWeather:
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, json=body))
    return OpenMeteoWeather(httpx.Client(transport=transport), 0.0, 0.0)


def test_reads_the_current_weather(forecast: OpenMeteoWeather) -> None:
    assert forecast.current() == Weather(Sky.RAIN, 19.5)


def test_asks_for_the_configured_place(
    forecast: OpenMeteoWeather, transport: RecordingTransport
) -> None:
    forecast.current()

    params = transport.requests[0].url.params
    assert (params["latitude"], params["longitude"]) == ("-19.9167", "-43.9345")


def test_a_server_error_means_the_weather_is_unavailable() -> None:
    with pytest.raises(WeatherUnavailableError):
        answering(500, {"error": True}).current()


def test_an_answer_without_current_conditions_means_the_weather_is_unavailable() -> None:
    with pytest.raises(WeatherUnavailableError):
        answering(200, {"daily": {}}).current()


def test_no_connection_means_the_weather_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    forecast = OpenMeteoWeather(httpx.Client(transport=httpx.MockTransport(refuse)), 0.0, 0.0)

    with pytest.raises(WeatherUnavailableError):
        forecast.current()


@pytest.mark.parametrize(
    ("code", "sky"),
    [
        (0, Sky.CLEAR),
        (3, Sky.CLOUDY),
        (45, Sky.FOG),
        (53, Sky.RAIN),
        (81, Sky.RAIN),
        (95, Sky.STORM),
    ],
)
def test_maps_wmo_codes_to_the_sky(code: int, sky: Sky) -> None:
    assert sky_from_wmo_code(code) is sky


def test_a_storm_counts_as_rain() -> None:
    assert Weather(Sky.STORM, 20.0).is_raining


def test_clouds_alone_are_not_rain() -> None:
    assert not Weather(Sky.CLOUDY, 20.0).is_raining
