import logging
from collections.abc import Callable
from datetime import date

from src.application.tools.saved_discoveries import SavedDiscoveries
from src.application.tools.seen_sources import SeenSources
from src.domain.discovery import Discovery, DiscoveryRepository, DiscoveryStorageError
from src.domain.language_model import ToolDefinition
from src.domain.tool import ToolError

ALLOWED_URL_PREFIXES = ("http://", "https://")

logger = logging.getLogger(__name__)


class SaveDiscoveryTool:
    def __init__(
        self,
        repository: DiscoveryRepository,
        seen_sources: SeenSources,
        today: Callable[[], date] = date.today,
        saved_discoveries: SavedDiscoveries | None = None,
    ) -> None:
        self._repository = repository
        self._seen_sources = seen_sources
        self._today = today
        self._saved_discoveries = (
            saved_discoveries if saved_discoveries is not None else SavedDiscoveries()
        )

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
                        "description": "URLs from your web_search results where you found it.",
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
        self._saved_discoveries.remember(discovery.title, file_name)
        logger.info("Discovery saved: %s (sources: %s)", file_name, ", ".join(discovery.sources))
        return self._result_message(file_name, discovery.title)

    @staticmethod
    def _result_message(file_name: str, title: str) -> str:
        """Invites the drawing right away, with the exact title the draw tool expects.

        Small models often announce "now I'll draw it" and never call the tool, or mix the
        title with the file name; the last thing they read is the best place to prevent both.
        """
        return (
            f"Saved as {file_name}. If this discovery deserves a drawing, call draw now with "
            f"discovery_title '{title}', without announcing it first: saying you will draw "
            "does not draw anything."
        )

    @staticmethod
    def _required_text(arguments: dict[str, object], name: str) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ToolError(f"the '{name}' argument must be a non-empty text")
        return value.strip()

    def _sources(self, arguments: dict[str, object]) -> tuple[str, ...]:
        sources = arguments.get("sources")
        if not isinstance(sources, list):
            raise ToolError("the 'sources' argument must be a list of URLs")
        urls = tuple(self._valid_url(source) for source in sources)
        self._ensure_sources_came_from_web_search(urls)
        return urls

    def _ensure_sources_came_from_web_search(self, urls: tuple[str, ...]) -> None:
        if self._seen_sources.is_empty:
            raise ToolError(
                "you have no web_search results to cite in this conversation (you did not "
                "search yet, or the search found nothing): search with other words and cite "
                "the URLs it returns, or do not save anything this time"
            )
        if not urls:
            raise ToolError("a discovery needs at least one source from your web_search results")
        for url in urls:
            if not self._seen_sources.contains(url):
                raise ToolError(
                    f"source '{url}' did not come from your web_search results: "
                    "search first and cite only URLs it returned"
                )

    @staticmethod
    def _valid_url(source: object) -> str:
        if not isinstance(source, str) or not source.strip().startswith(ALLOWED_URL_PREFIXES):
            raise ToolError(f"invalid source URL: '{source}'")
        return source.strip()
