"""JSON Schema of the WebSocket protocol, made from the Pydantic models.

Any visual client (the Godot world or another one) can follow these schemas without reading
Python. They are generated, never written by hand, so the contract never drifts from the code:
a test fails when the committed files are out of date.
"""

import json
from typing import Annotated, Any

from pydantic import Field, TypeAdapter

from src.infrastructure.world_messages import WorldEvent, WorldMessage
from src.infrastructure.world_requests import WorldReply, WorldRequest

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
WORLD_TO_BRAIN_FILE_NAME = "world-to-brain.schema.json"
BRAIN_TO_WORLD_FILE_NAME = "brain-to-world.schema.json"


def world_to_brain_schema() -> dict[str, Any]:
    """What a client may send: events and requests. Validation mode, because the brain
    validates these messages when they arrive."""
    adapter: TypeAdapter[WorldEvent | WorldRequest] = TypeAdapter(
        Annotated[WorldEvent | WorldRequest, Field(discriminator="type")]
    )
    return _described(
        adapter.json_schema(mode="validation"),
        title="Capivara IA: mundo para cérebro",
        description=(
            "Mensagens que um cliente visual manda ao cérebro: eventos (avisos, sem resposta) "
            "e pedidos (com request_id, sempre respondidos com o mesmo request_id)."
        ),
    )


def brain_to_world_schema() -> dict[str, Any]:
    """What the brain sends: orders for the body and replies to requests. Serialization
    mode, because these are the messages exactly as the brain writes them."""
    adapter: TypeAdapter[WorldMessage | WorldReply] = TypeAdapter(
        Annotated[WorldMessage | WorldReply, Field(discriminator="type")]
    )
    return _described(
        adapter.json_schema(mode="serialization"),
        title="Capivara IA: cérebro para mundo",
        description=(
            "Mensagens que o cérebro manda a um cliente visual: ordens para o corpo (para "
            "todos os clientes) e respostas a pedidos (só para o cliente que perguntou)."
        ),
    )


def protocol_schema_files() -> dict[str, str]:
    """Each schema file name with its content, ready to be written."""
    return {
        WORLD_TO_BRAIN_FILE_NAME: render_schema(world_to_brain_schema()),
        BRAIN_TO_WORLD_FILE_NAME: render_schema(brain_to_world_schema()),
    }


def render_schema(schema: dict[str, Any]) -> str:
    """Stable text: the same models always give the same bytes, so diffs show real changes."""
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def _described(schema: dict[str, Any], title: str, description: str) -> dict[str, Any]:
    _require_type_field(schema)
    return {"$schema": JSON_SCHEMA_DIALECT, "title": title, "description": description} | schema


def _require_type_field(schema: dict[str, Any]) -> None:
    """In Python "type" has a default, so Pydantic marks it optional. On the wire it is what
    tells the messages apart, so the contract requires it in every message."""
    for definition in schema.get("$defs", {}).values():
        if "const" not in definition.get("properties", {}).get("type", {}):
            continue
        required: list[str] = definition.setdefault("required", [])
        if "type" not in required:
            required.insert(0, "type")
