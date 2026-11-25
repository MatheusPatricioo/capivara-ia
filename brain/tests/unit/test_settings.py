from pathlib import Path

import pytest
from psycopg.conninfo import conninfo_to_dict
from pydantic import ValidationError

from src.domain.weather import Sky
from src.domain.world_clock import ClockMode
from src.infrastructure.ollama_language_model import OllamaGenerationOptions
from src.infrastructure.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def environment_without_discoveries_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCOVERIES_DIR", raising=False)


@pytest.fixture
def custom_discoveries_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("DISCOVERIES_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def environment_without_web_search_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEB_SEARCH_BACKEND", raising=False)


@pytest.fixture
def auto_web_search_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEB_SEARCH_BACKEND", "auto")


@pytest.fixture
def environment_without_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)


@pytest.fixture
def debug_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "LOUD")


@pytest.fixture
def custom_generation_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_NUM_PREDICT", "150")
    monkeypatch.setenv("OLLAMA_TEMPERATURE", "0.5")
    monkeypatch.setenv("OLLAMA_REPEAT_PENALTY", "1.2")


@pytest.fixture
def temperature_above_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_TEMPERATURE", "3")


@pytest.fixture
def zero_num_predict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_NUM_PREDICT", "0")


def test_generation_options_come_from_environment_variables(
    custom_generation_options: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.ollama_generation_options() == OllamaGenerationOptions(
        num_predict=150, temperature=0.5, repeat_penalty=1.2
    )


def test_rejects_a_temperature_above_two(temperature_above_the_limit: None) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rejects_a_num_predict_of_zero(zero_num_predict: None) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_log_level_defaults_to_info(environment_without_log_level: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.log_level == "INFO"


def test_log_level_comes_from_environment_variable(debug_log_level: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.log_level == "DEBUG"


def test_rejects_an_unknown_log_level(invalid_log_level: None) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_web_search_backend_defaults_to_duckduckgo(
    environment_without_web_search_backend: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.web_search_backend == "duckduckgo"


def test_web_search_backend_comes_from_environment_variable(
    auto_web_search_backend: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.web_search_backend == "auto"


def test_discoveries_dir_defaults_to_discoveries_folder_in_project_root(
    environment_without_discoveries_dir: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.discoveries_dir == PROJECT_ROOT / "discoveries"


def test_discoveries_dir_comes_from_environment_variable(custom_discoveries_dir: Path) -> None:
    settings = Settings(_env_file=None)

    assert settings.discoveries_dir == custom_discoveries_dir


@pytest.fixture
def environment_without_world_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORLD_SERVER_HOST", raising=False)
    monkeypatch.delenv("WORLD_SERVER_PORT", raising=False)


def test_world_server_listens_on_local_port_8765_by_default(
    environment_without_world_server: None,
) -> None:
    settings = Settings(_env_file=None)

    assert (settings.world_server_host, settings.world_server_port) == ("127.0.0.1", 8765)


@pytest.fixture
def environment_without_autonomous_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTONOMOUS_CYCLE_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("MAX_TOKENS_PER_HOUR", raising=False)


@pytest.fixture
def zero_max_tokens_per_hour(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_TOKENS_PER_HOUR", "0")


def test_autonomous_mode_defaults_to_two_minutes_and_60k_tokens_per_hour(
    environment_without_autonomous_settings: None,
) -> None:
    settings = Settings(_env_file=None)

    assert (settings.autonomous_cycle_interval_seconds, settings.max_tokens_per_hour) == (
        120.0,
        60000,
    )


def test_rejects_a_token_limit_of_zero(zero_max_tokens_per_hour: None) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_env_file_points_to_the_brain_folder_regardless_of_working_directory() -> None:
    assert Settings.model_config["env_file"] == PROJECT_ROOT / "brain" / ".env"


@pytest.fixture
def environment_without_memory_db(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("HOST", "PORT", "NAME", "USER", "PASSWORD"):
        monkeypatch.delenv(f"MEMORY_DB_{name}", raising=False)


@pytest.fixture
def memory_db_password(monkeypatch: pytest.MonkeyPatch) -> str:
    password = "secret-capybara"
    monkeypatch.setenv("MEMORY_DB_PASSWORD", password)
    return password


def test_memory_db_defaults_to_local_postgres_from_compose(
    environment_without_memory_db: None,
) -> None:
    settings = Settings(_env_file=None)

    assert (
        settings.memory_db_host,
        settings.memory_db_port,
        settings.memory_db_name,
        settings.memory_db_user,
    ) == ("127.0.0.1", 5432, "capybara_memory", "capybara")


def test_memory_db_password_comes_from_environment_variable(memory_db_password: str) -> None:
    settings = Settings(_env_file=None)

    assert settings.memory_db_password.get_secret_value() == memory_db_password


def test_memory_db_password_is_hidden_when_settings_are_printed(
    memory_db_password: str,
) -> None:
    settings = Settings(_env_file=None)

    assert memory_db_password not in repr(settings)


@pytest.fixture
def environment_without_memory_db_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MEMORY_DB_TIMEOUT_SECONDS", raising=False)


@pytest.fixture
def zero_memory_db_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_DB_TIMEOUT_SECONDS", "0")


@pytest.fixture
def custom_memory_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_DB_HOST", "db.local")
    monkeypatch.setenv("MEMORY_DB_PORT", "6543")
    monkeypatch.setenv("MEMORY_DB_NAME", "capybara_memory")
    monkeypatch.setenv("MEMORY_DB_USER", "capybara")
    monkeypatch.setenv("MEMORY_DB_PASSWORD", "my secret")


def test_memory_db_timeout_defaults_to_five_seconds(
    environment_without_memory_db_timeout: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.memory_db_timeout_seconds == 5.0


def test_rejects_a_memory_db_timeout_of_zero(zero_memory_db_timeout: None) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_memory_db_conninfo_comes_from_the_memory_db_variables(custom_memory_db: None) -> None:
    settings = Settings(_env_file=None)

    assert conninfo_to_dict(settings.memory_db_conninfo()) == {
        "host": "db.local",
        "port": "6543",
        "dbname": "capybara_memory",
        "user": "capybara",
        "password": "my secret",
    }


@pytest.fixture
def environment_without_memory_recall_min_similarity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MEMORY_RECALL_MIN_SIMILARITY", raising=False)


@pytest.fixture
def memory_recall_min_similarity_above_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_RECALL_MIN_SIMILARITY", "1.5")


def test_memory_recall_min_similarity_defaults_to_the_measured_value(
    environment_without_memory_recall_min_similarity: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.memory_recall_min_similarity == 0.50


def test_rejects_a_memory_recall_min_similarity_above_one(
    memory_recall_min_similarity_above_one: None,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.fixture
def environment_without_suggestion_repeat_min_similarity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUGGESTION_REPEAT_MIN_SIMILARITY", raising=False)


@pytest.fixture
def suggestion_repeat_min_similarity_below_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUGGESTION_REPEAT_MIN_SIMILARITY", "-0.1")


def test_suggestion_repeat_min_similarity_defaults_to_the_measured_value(
    environment_without_suggestion_repeat_min_similarity: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.suggestion_repeat_min_similarity == 0.80


def test_rejects_a_suggestion_repeat_min_similarity_below_zero(
    suggestion_repeat_min_similarity_below_zero: None,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.fixture
def environment_without_world_clock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORLD_CLOCK_MODE", raising=False)


@pytest.fixture
def fast_world_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORLD_CLOCK_MODE", "fast")


@pytest.fixture
def unknown_world_clock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORLD_CLOCK_MODE", "turbo")


def test_world_clock_mode_defaults_to_real_time(
    environment_without_world_clock_mode: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.world_clock_mode is ClockMode.REAL


def test_world_clock_mode_comes_from_environment_variable(fast_world_clock: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.world_clock_mode is ClockMode.FAST


def test_rejects_an_unknown_world_clock_mode(unknown_world_clock_mode: None) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.fixture
def environment_without_weather_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEATHER_OVERRIDE", raising=False)


@pytest.fixture
def rain_weather_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEATHER_OVERRIDE", "rain")


def test_weather_follows_the_forecast_by_default(
    environment_without_weather_override: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.weather_override is None


def test_weather_override_comes_from_environment_variable(rain_weather_override: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.weather_override is Sky.RAIN
