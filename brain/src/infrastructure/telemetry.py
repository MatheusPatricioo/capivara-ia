"""Installs OpenTelemetry tracing and sends the spans to Langfuse.

Until tracing_to_langfuse runs, the spans the brain opens are no-ops (the OpenTelemetry
API with no SDK behind it). With TRACING_ENABLED=true in brain/.env, it installs the SDK:
spans are batched in the background and sent over OTLP/HTTP to a Langfuse running in
Docker (compose.observability.yaml). If Langfuse is offline, the batches are dropped
with a warning in the log and the capybara goes on living: tracing never stops her.
"""

import base64
import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.infrastructure.prompt_loader import prompt_versions, prompts_version
from src.infrastructure.settings import Settings

logger = logging.getLogger(__name__)

BRAIN_SERVICE_NAME = "capivara-brain"
LANGFUSE_TRACES_PATH = "/api/public/otel/v1/traces"
# The ingestion version Langfuse's OpenTelemetry guide asks for.
LANGFUSE_INGESTION_VERSION = "4"
# Seconds an export waits for Langfuse, also when the brain stops and flushes the last spans.
EXPORT_TIMEOUT_SECONDS = 5
# Langfuse shows the version on every observation and can filter traces by it.
VERSION_ATTRIBUTE = "langfuse.version"
PROMPTS_VERSION_METADATA = "langfuse.trace.metadata.prompts_version"
PROMPTS_VERSION_RESOURCE = "capybara.prompts.version"
PROMPT_RESOURCE_PREFIX = "capybara.prompt."


class PromptVersionSpanProcessor(SpanProcessor):
    """Stamps every span with the version of the prompts, so traces made with different
    prompts can be told apart and compared in the panel."""

    def __init__(self, version: str) -> None:
        self._version = version

    def on_start(self, span: Span, parent_context: context.Context | None = None) -> None:
        span.set_attribute(VERSION_ATTRIBUTE, self._version)
        span.set_attribute(PROMPTS_VERSION_METADATA, self._version)


def langfuse_traces_endpoint(host: str) -> str:
    return host.rstrip("/") + LANGFUSE_TRACES_PATH


def langfuse_headers(public_key: str, secret_key: str) -> dict[str, str]:
    """Langfuse takes the project's key pair as HTTP Basic authentication."""
    credentials = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode("ascii")
    return {
        "Authorization": f"Basic {credentials}",
        "x-langfuse-ingestion-version": LANGFUSE_INGESTION_VERSION,
    }


def build_tracer_provider(
    span_processor: SpanProcessor, versions: Mapping[str, str]
) -> TracerProvider:
    """The SDK side: who the spans come from (the resource), the prompt version on every
    span, and where they go (span_processor)."""
    version = prompts_version(dict(versions))
    resource = Resource.create(
        {
            SERVICE_NAME: BRAIN_SERVICE_NAME,
            PROMPTS_VERSION_RESOURCE: version,
            **{PROMPT_RESOURCE_PREFIX + name: value for name, value in versions.items()},
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(PromptVersionSpanProcessor(version))
    provider.add_span_processor(span_processor)
    return provider


@contextmanager
def tracing_to_langfuse(settings: Settings) -> Iterator[None]:
    """Traces everything inside the with block when tracing is on, and sends the last
    spans before leaving it. Does nothing when it is off."""
    if not settings.tracing_enabled:
        yield
        return
    exporter = OTLPSpanExporter(
        endpoint=langfuse_traces_endpoint(settings.langfuse_host),
        headers=langfuse_headers(
            settings.langfuse_public_key, settings.langfuse_secret_key.get_secret_value()
        ),
        timeout=EXPORT_TIMEOUT_SECONDS,
    )
    versions = prompt_versions()
    provider = build_tracer_provider(BatchSpanProcessor(exporter), versions)
    trace.set_tracer_provider(provider)
    logger.info(
        "Tracing to Langfuse at %s (prompts version %s)",
        settings.langfuse_host,
        prompts_version(versions),
    )
    try:
        yield
    finally:
        provider.shutdown()
