"""Builds the sky of her world (clock + weather) and describes it in the terminal."""

import httpx

from src.application.world_now import SKY_NAMES
from src.application.world_sky import SkyView, WorldSky
from src.domain.weather import WeatherForecast
from src.domain.world_clock import ClockMode, DayPhase
from src.infrastructure.fixed_weather import FixedWeatherForecast
from src.infrastructure.open_meteo_weather import OpenMeteoWeather
from src.infrastructure.settings import SECONDS_PER_MINUTE, Settings

CLOCK_MODE_NAMES = {ClockMode.REAL: "horário real", ClockMode.FAST: "dia rápido"}
PHASE_NAMES = {DayPhase.DAY: "dia", DayPhase.NIGHT: "noite"}


def build_weather_forecast(settings: Settings, client: httpx.Client) -> WeatherForecast | None:
    """The fixed sky of WEATHER_OVERRIDE, the real forecast, or None when it is switched off."""
    if settings.weather_override is not None:
        return FixedWeatherForecast(settings.weather_override)
    if not settings.weather_enabled:
        return None
    return OpenMeteoWeather(client, settings.weather_latitude, settings.weather_longitude)


def build_world_sky(settings: Settings, client: httpx.Client) -> WorldSky:
    return WorldSky(
        settings.world_clock(),
        build_weather_forecast(settings, client),
        weather_refresh_seconds=settings.weather_refresh_minutes * SECONDS_PER_MINUTE,
    )


def describe_sky(settings: Settings, view: SkyView) -> str:
    """Two lines for the terminal: which clock her world follows, and its weather."""
    mode = CLOCK_MODE_NAMES[settings.world_clock_mode]
    if settings.world_clock_mode is ClockMode.FAST:
        mode += f", um dia a cada {settings.world_fast_day_minutes:g} min"
    world_time = view.world_time
    clock_line = (
        f"Relógio do mundo: {mode}. Lá agora são "
        f"{world_time.time_of_day:%H:%M} ({PHASE_NAMES[world_time.phase]})."
    )
    return f"{clock_line}\n{_describe_weather(settings, view)}"


def _describe_weather(settings: Settings, view: SkyView) -> str:
    if settings.weather_override is not None:
        return f"Clima: fixo em {SKY_NAMES[settings.weather_override]} (WEATHER_OVERRIDE)."
    if not settings.weather_enabled:
        return "Clima: desligado (WEATHER_ENABLED=false), céu sempre limpo."
    if view.weather is None:
        return f"Clima em {settings.weather_place_name}: sem previsão agora."
    return (
        f"Clima em {settings.weather_place_name}: {SKY_NAMES[view.weather.sky]}, "
        f"{view.weather.temperature_celsius:.0f} °C."
    )
