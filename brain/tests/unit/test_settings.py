from pathlib import Path

import pytest
from pydantic import ValidationError

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
def environment_without_chalkboard_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHALKBOARD_CAPACITY", raising=False)


@pytest.fixture
def custom_chalkboard_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHALKBOARD_CAPACITY", "5")


@pytest.fixture
def zero_chalkboard_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHALKBOARD_CAPACITY", "0")


def test_chalkboard_capacity_defaults_to_three(
    environment_without_chalkboard_capacity: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.chalkboard_capacity == 3


def test_chalkboard_capacity_comes_from_environment_variable(
    custom_chalkboard_capacity: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.chalkboard_capacity == 5


def test_rejects_a_chalkboard_capacity_of_zero(zero_chalkboard_capacity: None) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_env_file_points_to_the_brain_folder_regardless_of_working_directory() -> None:
    assert Settings.model_config["env_file"] == PROJECT_ROOT / "brain" / ".env"
