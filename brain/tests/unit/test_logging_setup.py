import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.infrastructure.logging_setup import (
    BRAIN_LOGGER_NAME,
    DATABASE_LOGGER_NAME,
    configure_logging,
)


@pytest.fixture(autouse=True)
def restore_configured_loggers() -> Iterator[None]:
    configured_loggers = [
        logging.getLogger(BRAIN_LOGGER_NAME),
        logging.getLogger(DATABASE_LOGGER_NAME),
    ]
    original_levels = [configured_logger.level for configured_logger in configured_loggers]
    yield
    for configured_logger, original_level in zip(configured_loggers, original_levels, strict=True):
        for handler in configured_logger.handlers[:]:
            handler.close()
            configured_logger.removeHandler(handler)
        configured_logger.setLevel(original_level)


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


def test_writes_database_warnings_to_the_log_file(log_file: Path) -> None:
    configure_logging(log_file, "INFO")

    logging.getLogger("psycopg.pool").warning("error connecting in 'discovery-memory'")

    assert "error connecting in 'discovery-memory'" in log_file.read_text(encoding="utf-8")


def test_skips_database_records_below_warning(log_file: Path) -> None:
    configure_logging(log_file, "DEBUG")

    logging.getLogger("psycopg.pool").info("connection given by 'discovery-memory'")

    assert log_file.read_text(encoding="utf-8") == ""


def test_does_not_print_database_warnings_in_the_terminal(
    log_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging(log_file, "INFO")

    logging.getLogger("psycopg.pool").warning("couldn't stop thread 'discovery-memory-worker-0'")

    assert capsys.readouterr() == ("", "")
