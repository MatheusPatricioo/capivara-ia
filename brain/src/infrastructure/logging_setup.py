import logging
from pathlib import Path

BRAIN_LOGGER_NAME = "src"
# psycopg logs a warning on every failed reconnection while the memory database is
# offline. Without a handler of its own, Python would print those in the terminal.
DATABASE_LOGGER_NAME = "psycopg"
DATABASE_LOG_LEVEL = logging.WARNING
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(log_file: Path, level: str) -> None:
    """Sends the brain's log records to a file only, so nothing shows up in the chat.

    The database driver's warnings go to the same file, for the same reason.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    brain_logger = logging.getLogger(BRAIN_LOGGER_NAME)
    brain_logger.setLevel(level)
    brain_logger.addHandler(file_handler)
    database_logger = logging.getLogger(DATABASE_LOGGER_NAME)
    database_logger.setLevel(DATABASE_LOG_LEVEL)
    database_logger.addHandler(file_handler)
