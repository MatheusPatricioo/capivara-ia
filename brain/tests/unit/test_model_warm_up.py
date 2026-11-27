import logging

import pytest

from src.domain.language_model import LanguageModelError
from src.infrastructure.model_warm_up import warm_up_in_background

JOIN_TIMEOUT_SECONDS = 2.0


class RecordingModel:
    def __init__(self) -> None:
        self.warm_up_count = 0

    def warm_up(self) -> None:
        self.warm_up_count += 1


class OfflineModel:
    def warm_up(self) -> None:
        raise LanguageModelError("Ollama is offline")


@pytest.fixture
def model() -> RecordingModel:
    return RecordingModel()


def test_loads_the_model_once(model: RecordingModel) -> None:
    warm_up_in_background(model).join(JOIN_TIMEOUT_SECONDS)

    assert model.warm_up_count == 1


def test_runs_in_a_daemon_thread_so_it_never_holds_the_brain_open(
    model: RecordingModel,
) -> None:
    thread = warm_up_in_background(model)
    thread.join(JOIN_TIMEOUT_SECONDS)

    assert thread.daemon


def test_logs_how_long_the_model_took_to_load(
    model: RecordingModel, caplog: pytest.LogCaptureFixture
) -> None:
    clock_readings = iter([10.0, 42.5])

    with caplog.at_level(logging.INFO):
        warm_up_in_background(model, clock=lambda: next(clock_readings)).join(JOIN_TIMEOUT_SECONDS)

    assert "ready (32.5s)" in caplog.text


def test_a_model_that_cannot_load_is_only_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warm_up_in_background(OfflineModel()).join(JOIN_TIMEOUT_SECONDS)

    assert "Could not load her model ahead of time" in caplog.text
