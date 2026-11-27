from pathlib import Path
from typing import Any, get_args

import pytest

from src.export_protocol_schema import PROTOCOL_DOCS_DIR, export_protocol_schema
from src.infrastructure.protocol_schema import (
    brain_to_world_schema,
    protocol_schema_files,
    world_to_brain_schema,
)
from src.infrastructure.world_messages import WorldEvent, WorldMessage
from src.infrastructure.world_requests import WorldReply, WorldRequest


def message_types(*unions: Any) -> set[str]:
    """The "type" value of every model in the given unions."""
    return {model.model_fields["type"].default for union in unions for model in get_args(union)}


def schema_types(schema: dict[str, Any]) -> set[str]:
    return set(schema["discriminator"]["mapping"])


def definitions_without_required_type(schema: dict[str, Any]) -> list[str]:
    return [
        name
        for name, definition in schema["$defs"].items()
        if "const" in definition.get("properties", {}).get("type", {})
        and "type" not in definition.get("required", [])
    ]


@pytest.mark.parametrize("file_name", sorted(protocol_schema_files()))
def test_the_committed_schema_matches_the_models(file_name: str) -> None:
    committed_file = PROTOCOL_DOCS_DIR / file_name

    assert committed_file.read_text(encoding="utf-8") == protocol_schema_files()[file_name], (
        "docs/protocol is out of date: run `python -m src.export_protocol_schema` in brain/"
    )


def test_world_to_brain_lists_every_event_and_request() -> None:
    assert schema_types(world_to_brain_schema()) == message_types(WorldEvent, WorldRequest)


def test_brain_to_world_lists_every_message_and_reply() -> None:
    assert schema_types(brain_to_world_schema()) == message_types(WorldMessage, WorldReply)


@pytest.mark.parametrize("schema", [world_to_brain_schema(), brain_to_world_schema()])
def test_every_message_requires_its_type(schema: dict[str, Any]) -> None:
    assert definitions_without_required_type(schema) == []


def test_a_request_requires_its_request_id() -> None:
    drawing_request = world_to_brain_schema()["$defs"]["GetDrawingRequest"]

    assert drawing_request["required"] == ["type", "request_id", "id"]


def test_the_schemas_declare_their_json_schema_dialect() -> None:
    assert world_to_brain_schema()["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_export_writes_every_schema_file(tmp_path: Path) -> None:
    written_files = export_protocol_schema(tmp_path)

    written_contents = {
        schema_file.name: schema_file.read_text(encoding="utf-8") for schema_file in written_files
    }
    assert written_contents == protocol_schema_files()
