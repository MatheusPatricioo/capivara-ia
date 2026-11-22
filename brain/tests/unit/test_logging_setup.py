import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.infrastructure.logging_setup import BRAIN_LOGGER_NAME, configure_logging


@pytest.fixture(autouse=True)
def restore_brain_logger() -> Iterator[None]:
    brain_logger = logging.getLogger(BRAIN_LOGGER_NAME)
    original_level = brain_logger.level
    yield
    for handler in brain_logger.handlers[:]:
        handler.close()
        brain_logger.removeHandler(handler)
    brain_logger.setLevel(original_level)


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    return tmp_path / "logs" / "capybara.log"


def test_writes_brain_records_to_the_log_file(log_file: Path) -> None:
    configure_logging(log_file, "INFO")

    logging.getLogger("src.application.conversation").info("Tool call: web_search")

    assert "Tool call: web_search" in log_file.read_text(encoding="utf-8")


def test_skips_records_below_the_configured_level(log_file: Path) -> None:
    configure_logging(log_file, "WARNING")

    logging.getLogger("src.application.conversation").info("Tool call: web_search")

    assert log_file.read_text(encoding="utf-8") == ""


def test_does_not_print_brain_records_in_the_terminal(
    log_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging(log_file, "INFO")

    logging.getLogger("src.application.conversation").warning("Step limit reached")

    assert capsys.readouterr() == ("", "")
