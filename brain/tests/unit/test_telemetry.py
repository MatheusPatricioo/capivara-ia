import base64

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.infrastructure import telemetry
from src.infrastructure.prompt_loader import prompts_version
from src.infrastructure.settings import Settings
from src.infrastructure.telemetry import (
    build_tracer_provider,
    langfuse_headers,
    langfuse_traces_endpoint,
    tracing_to_langfuse,
)

PROMPT_VERSIONS = {"capybara": "aaaaaaaaaaaa", "letter": "bbbbbbbbbbbb"}


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture
def provider(exporter: InMemorySpanExporter) -> TracerProvider:
    return build_tracer_provider(SimpleSpanProcessor(exporter), PROMPT_VERSIONS)


def test_the_endpoint_is_langfuse_otlp_traces_path() -> None:
    assert (
        langfuse_traces_endpoint("http://localhost:3000/")
        == "http://localhost:3000/api/public/otel/v1/traces"
    )


def test_the_keys_go_as_basic_authentication() -> None:
    headers = langfuse_headers("pk-lf-test", "sk-lf-test")

    encoded_credentials = headers["Authorization"].removeprefix("Basic ")
    assert base64.b64decode(encoded_credentials).decode() == "pk-lf-test:sk-lf-test"


def test_spans_come_from_the_brain_service(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    with provider.get_tracer("tests").start_as_current_span("autonomous_cycle"):
        pass

    (span,) = exporter.get_finished_spans()
    assert span.resource.attributes["service.name"] == "capivara-brain"


def test_every_span_carries_the_version_of_the_prompts(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    with provider.get_tracer("tests").start_as_current_span("autonomous_cycle"):
        pass

    (span,) = exporter.get_finished_spans()
    assert (span.attributes or {})["langfuse.version"] == prompts_version(PROMPT_VERSIONS)


def test_the_version_of_each_prompt_is_in_the_resource(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    with provider.get_tracer("tests").start_as_current_span("autonomous_cycle"):
        pass

    (span,) = exporter.get_finished_spans()
    assert span.resource.attributes["capybara.prompt.letter"] == "bbbbbbbbbbbb"


def test_tracing_turned_off_installs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    installed_providers: list[trace.TracerProvider] = []
    monkeypatch.setattr(telemetry.trace, "set_tracer_provider", installed_providers.append)

    with tracing_to_langfuse(Settings(tracing_enabled=False)):
        pass

    assert installed_providers == []


def test_tracing_turned_on_installs_a_provider_and_shuts_it_down_at_the_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_providers: list[TracerProvider] = []
    shut_down_providers: list[TracerProvider] = []
    monkeypatch.setattr(telemetry.trace, "set_tracer_provider", installed_providers.append)

    def record_shutdown(provider: TracerProvider) -> None:
        shut_down_providers.append(provider)

    monkeypatch.setattr(TracerProvider, "shutdown", record_shutdown)

    with tracing_to_langfuse(Settings(tracing_enabled=True)):
        pass

    assert len(installed_providers) == 1
    assert shut_down_providers == installed_providers
