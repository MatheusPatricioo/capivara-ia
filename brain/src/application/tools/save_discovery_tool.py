import logging
from collections.abc import Callable
from datetime import date

from src.domain.discovery import Discovery, DiscoveryRepository, DiscoveryStorageError
from src.domain.language_model import ToolDefinition
from src.domain.tool import ToolError

ALLOWED_URL_PREFIXES = ("http://", "https://")

logger = logging.getLogger(__name__)


class SaveDiscoveryTool:
    def __init__(
        self,
        repository: DiscoveryRepository,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._repository = repository
        self._today = today

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="save_discovery",
            description=(
                "Saves something interesting you learned in your discoveries folder. "
                "The file name is chosen automatically."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short title of the discovery."},
                    "topic": {"type": "string", "description": "General theme, e.g. 'stars'."},
                    "summary": {
                        "type": "string",
                        "description": "What you learned, written in your own words.",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "URLs of the pages where you found it.",
                    },
                },
                "required": ["title", "topic", "summary", "sources"],
            },
        )

    def run(self, arguments: dict[str, object]) -> str:
        discovery = Discovery(
            title=self._required_text(arguments, "title"),
            topic=self._required_text(arguments, "topic"),
            summary=self._required_text(arguments, "summary"),
            sources=self._sources(arguments),
            discovered_on=self._today(),
        )
        try:
            file_name = self._repository.save(discovery)
        except DiscoveryStorageError as error:
            raise ToolError(f"could not save the discovery: {error}") from error
        logger.info("Discovery saved: %s (sources: %s)", file_name, ", ".join(discovery.sources))
        return f"Saved as {file_name}"

    @staticmethod
    def _required_text(arguments: dict[str, object], name: str) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ToolError(f"the '{name}' argument must be a non-empty text")
        return value.strip()

    @staticmethod
    def _sources(arguments: dict[str, object]) -> tuple[str, ...]:
        sources = arguments.get("sources")
        if not isinstance(sources, list):
            raise ToolError("the 'sources' argument must be a list of URLs")
        return tuple(SaveDiscoveryTool._valid_url(source) for source in sources)

    @staticmethod
    def _valid_url(source: object) -> str:
        if not isinstance(source, str) or not source.strip().startswith(ALLOWED_URL_PREFIXES):
            raise ToolError(f"invalid source URL: '{source}'")
        return source.strip()
