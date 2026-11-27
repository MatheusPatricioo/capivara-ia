"""Writes the JSON Schema of the WebSocket protocol into docs/protocol/.

    cd brain
    python -m src.export_protocol_schema

Run it after changing any message in world_messages.py or world_requests.py, and commit the
files: a test fails while they are out of date.
"""

from pathlib import Path

from src.infrastructure.protocol_schema import protocol_schema_files

# brain/src/this_file.py -> the repository root. Not taken from settings, which would import
# the database driver just to write two JSON files.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_DOCS_DIR = PROJECT_ROOT / "docs" / "protocol"


def export_protocol_schema(target_dir: Path) -> list[Path]:
    """Writes every schema file into target_dir and returns their paths."""
    target_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []
    for file_name, content in protocol_schema_files().items():
        schema_file = target_dir / file_name
        schema_file.write_text(content, encoding="utf-8", newline="\n")
        written_files.append(schema_file)
    return written_files


def main() -> None:
    for schema_file in export_protocol_schema(PROTOCOL_DOCS_DIR):
        print(f"Escrito: {schema_file}")


if __name__ == "__main__":
    main()
