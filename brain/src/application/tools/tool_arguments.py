"""Tool arguments as Pydantic models: one class is both the schema and the validation.

The JSON Schema the model receives (ToolDefinition.parameters) is generated from the same
class that validates its answer, so the two can never drift apart. When the model sends
something that does not fit, the tool refuses with a short, field-by-field message; the
conversation returns it as the tool result, and the model corrects itself on the next step.
"""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError
from pydantic_core import ErrorDetails

from src.domain.tool import ToolError

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
"""A text with something in it; surrounding spaces are removed."""

# Pydantic error types turned into words a small model understands.
FRIENDLY_MESSAGES = {
    "missing": "is required",
    "string_type": "must be a text",
    "string_too_short": "must not be empty",
    "list_type": "must be a list",
}
SCHEMA_NOISE_KEYS = frozenset({"title"})


class ToolArguments(BaseModel):
    """Base for every tool's arguments.

    - extra="ignore": small models sometimes add fields nobody asked for; they are dropped.
    - Types are not coerced between kinds (a number is not accepted as a text).
    """

    model_config = ConfigDict(extra="ignore", frozen=True)


def tool_parameters(arguments_model: type[ToolArguments]) -> dict[str, object]:
    """The JSON Schema for ToolDefinition.parameters, without Pydantic's "title" noise."""
    schema: dict[str, object] = _without_noise(arguments_model.model_json_schema())
    return schema


def parse_arguments[ArgumentsT: ToolArguments](
    arguments_model: type[ArgumentsT], arguments: dict[str, object]
) -> ArgumentsT:
    """The validated arguments, or a ToolError saying what is wrong with each field."""
    try:
        return arguments_model.model_validate(arguments)
    except ValidationError as error:
        problems = "; ".join(_describe(detail) for detail in error.errors())
        raise ToolError(f"invalid arguments: {problems}") from error


def _describe(detail: ErrorDetails) -> str:
    field = ".".join(str(part) for part in detail["loc"]) or "arguments"
    message = FRIENDLY_MESSAGES.get(detail["type"], _plain(detail["msg"]))
    return f"'{field}' {message}"


def _plain(message: str) -> str:
    """Pydantic prefixes custom errors with "Value error, "; the rest is our own message."""
    return message.removeprefix("Value error, ")


def _without_noise(schema: Any) -> Any:
    """Titles repeat the field names: they only cost tokens in every request."""
    if isinstance(schema, dict):
        return {
            key: _without_noise(value)
            for key, value in schema.items()
            if key not in SCHEMA_NOISE_KEYS or not isinstance(value, str)
        }
    if isinstance(schema, list):
        return [_without_noise(item) for item in schema]
    return schema
