import logging
from pathlib import Path

import pytest

from src.capybara_chat import load_world_voice
from src.infrastructure.settings import Settings


@pytest.fixture
def settings_without_voice_file(tmp_path: Path) -> Settings:
    return Settings(voice_model_path=tmp_path / "missing-voice.onnx")


def test_without_the_voice_file_she_has_no_voice(settings_without_voice_file: Settings) -> None:
    assert load_world_voice(settings_without_voice_file) is None


def test_without_the_voice_file_the_reason_is_logged(
    settings_without_voice_file: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        load_world_voice(settings_without_voice_file)

    assert "Her voice is off" in caplog.text
