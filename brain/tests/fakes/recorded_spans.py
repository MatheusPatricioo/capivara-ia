from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Tracer


class RecordedSpans:
    """A real OpenTelemetry tracer that keeps the finished spans in memory instead of
    sending them anywhere. Its own provider, so no test touches the global one."""

    def __init__(self) -> None:
        self._exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        self.tracer: Tracer = provider.get_tracer("tests")

    @property
    def finished(self) -> tuple[ReadableSpan, ...]:
        return self._exporter.get_finished_spans()

    def named(self, span_name: str) -> ReadableSpan:
        """The only finished span with this name."""
        (span,) = (span for span in self.finished if span.name == span_name)
        return span

    def names(self) -> list[str]:
        return [span.name for span in self.finished]
