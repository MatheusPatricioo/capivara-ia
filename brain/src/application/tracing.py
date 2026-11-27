"""Names of the span attributes the brain records, in one place.

The code only depends on the OpenTelemetry API, which does nothing until the program
installs an SDK (see src/infrastructure/telemetry.py), the same way `logging` does
nothing visible until it is configured. Where the OpenTelemetry GenAI conventions have a
name, it is used; input, output and the observation type use Langfuse's names, because
the conventions have none for an agent turn. They are plain strings: nothing here
imports Langfuse.
"""

import json

from opentelemetry.trace import Span, Status, StatusCode

# OpenTelemetry GenAI semantic conventions.
OPERATION_NAME = "gen_ai.operation.name"
PROVIDER_NAME = "gen_ai.system"
REQUEST_MODEL = "gen_ai.request.model"
INPUT_TOKENS = "gen_ai.usage.input_tokens"
OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
TOOL_NAME = "gen_ai.tool.name"
TOOL_ARGUMENTS = "gen_ai.tool.call.arguments"
TOOL_RESULT = "gen_ai.tool.call.result"
AGENT_NAME = "gen_ai.agent.name"

# Langfuse attributes, for what the conventions do not cover.
OBSERVATION_TYPE = "langfuse.observation.type"
OBSERVATION_INPUT = "langfuse.observation.input"
OBSERVATION_OUTPUT = "langfuse.observation.output"
MODEL_PARAMETERS = "langfuse.observation.model.parameters"
SESSION_ID = "langfuse.session.id"
OBSERVATION_METADATA_PREFIX = "langfuse.observation.metadata."

AGENT = "agent"
GENERATION = "generation"
TOOL = "tool"

CAPYBARA_AGENT_NAME = "capivara"


def to_json(value: object) -> str:
    """Span attributes only hold strings and numbers: structured values go as JSON."""
    return json.dumps(value, ensure_ascii=False, default=str)


def record_input(span: Span, value: object) -> None:
    span.set_attribute(OBSERVATION_INPUT, value if isinstance(value, str) else to_json(value))


def record_output(span: Span, value: object) -> None:
    span.set_attribute(OBSERVATION_OUTPUT, value if isinstance(value, str) else to_json(value))


def record_metadata(span: Span, key: str, value: str | int | float | bool) -> None:
    span.set_attribute(OBSERVATION_METADATA_PREFIX + key, value)


def mark_failed(span: Span, reason: str) -> None:
    """For a failure the code handles itself: the span ends normally but shows as an error."""
    span.set_status(Status(StatusCode.ERROR, reason))
