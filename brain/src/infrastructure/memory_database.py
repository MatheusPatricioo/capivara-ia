"""Creates side databases (for tests and evals) with the same schema Docker applies.

The real memory database is created by Docker from brain/database/init/. Tests and evals
use their own databases on the same server ("<name>_test", "<name>_eval"), so they never
touch the capybara's real memory.
"""

import psycopg
from psycopg import sql

from src.infrastructure.settings import PROJECT_ROOT, Settings

SCHEMA_FILE = PROJECT_ROOT / "brain" / "database" / "init" / "001_create_discoveries.sql"
MAINTENANCE_DATABASE = "postgres"
CONNECT_TIMEOUT_SECONDS = 3


def with_database(settings: Settings, database: str) -> Settings:
    """The same settings pointing at another database of the same server."""
    return settings.model_copy(update={"memory_db_name": database})


def prepare_side_database(settings: Settings, suffix: str) -> Settings:
    """Creates "<memory_db_name>_<suffix>" when missing, applies the schema, returns its settings.

    Raises psycopg.OperationalError when the server is offline.
    """
    side_settings = with_database(settings, f"{settings.memory_db_name}_{suffix}")
    create_database_if_missing(side_settings)
    apply_schema(side_settings)
    return side_settings


def create_database_if_missing(settings: Settings) -> None:
    # CREATE DATABASE cannot run inside a transaction, hence autocommit.
    maintenance_settings = with_database(settings, MAINTENANCE_DATABASE)
    with psycopg.connect(
        maintenance_settings.memory_db_conninfo(),
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    ) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (settings.memory_db_name,)
        ).fetchone()
        if exists is None:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(settings.memory_db_name))
            )


def apply_schema(settings: Settings) -> None:
    # The schema file only uses IF NOT EXISTS, so applying it on every run is harmless.
    with psycopg.connect(
        settings.memory_db_conninfo(), connect_timeout=CONNECT_TIMEOUT_SECONDS
    ) as connection:
        connection.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
