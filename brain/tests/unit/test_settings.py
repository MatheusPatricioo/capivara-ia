from pathlib import Path

import pytest

from src.infrastructure.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def environment_without_discoveries_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCOVERIES_DIR", raising=False)


@pytest.fixture
def custom_discoveries_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("DISCOVERIES_DIR", str(tmp_path))
    return tmp_path


def test_discoveries_dir_defaults_to_discoveries_folder_in_project_root(
    environment_without_discoveries_dir: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.discoveries_dir == PROJECT_ROOT / "discoveries"


def test_discoveries_dir_comes_from_environment_variable(custom_discoveries_dir: Path) -> None:
    settings = Settings(_env_file=None)

    assert settings.discoveries_dir == custom_discoveries_dir
