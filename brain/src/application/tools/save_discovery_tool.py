import logging
from collections.abc import Callable
from datetime import date

from src.application.chalkboard_artist import PinnedDrawing
from src.application.tools.conversation_discoveries import ConversationDiscoveries
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
        illustrate: Callable[[Discovery], PinnedDrawing | None] | None = None,
        saved_discoveries: ConversationDiscoveries | None = None,
        follow_up: str = "",
    ) -> None:
        """illustrate is offered every discovery right after it is saved (None: no drawing).

        saved_discoveries, when given, receives every discovery saved in this conversation.
        follow_up is added at the end of every successful save result (like the invitation
        to suggest something for her world): a hint in the right moment works better than a
        rule in the system prompt, which she reads long before.
        """
        self._repository = repository
        self._seen_sources = seen_sources
        self._today = today
        self._illustrate = illustrate
        self._saved_discoveries = saved_discoveries
        self._follow_up = follow_up.strip()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="save_discovery",
            description=(
                "Saves something interesting you learned in your discoveries folder. "
                "The file name is chosen automatically. Title, topic and summary are always "
                "written in Brazilian Portuguese, even when the pages were in another language."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short title, in Brazilian Portuguese.",
                    },
                    "topic": {
                        "type": "string",
                        "description": "General theme in Brazilian Portuguese, e.g. 'estrelas'.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "What you learned, in your own words, in Portuguese.",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "URLs from your web_search results where you found it. "
                            "If left out, the results of your latest search are cited."
                        ),
                    },
                },
                "required": ["title", "topic", "summary"],
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
        if self._saved_discoveries is not None:
            self._saved_discoveries.remember(discovery)
        pinned_drawing = self._illustrate(discovery) if self._illustrate else None
        return self._with_follow_up(self._result_message(file_name, pinned_drawing))

    def _with_follow_up(self, message: str) -> str:
        """The follow-up comes last, the part of a tool result the model follows best."""
        if not self._follow_up:
            return message
        return f"{message} {self._follow_up}"

    def _result_message(self, file_name: str, pinned_drawing: PinnedDrawing | None) -> str:
        """Tells her what already happened, drawing included, so she only has to tell it.

        Asking her to call a draw tool made her promise drawings she never made.
        """
        message = f"Saved as {file_name}."
        if self._illustrate is None:
            return message
        if pinned_drawing is None:
            return f"{message} At your chalkboard, this one did not become a drawing."
        return f"{message} {_describe_drawing(pinned_drawing)}"

    @staticmethod
    def _required_text(arguments: dict[str, object], name: str) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ToolError(f"the '{name}' argument must be a non-empty text")
        return value.strip()

    def _sources(self, arguments: dict[str, object]) -> tuple[str, ...]:
        sources = arguments.get("sources")
        if sources is None:
            return self._latest_search_results()
        if not isinstance(sources, list):
            raise ToolError("the 'sources' argument must be a list of URLs")
        urls = tuple(self._valid_url(source) for source in sources)
        self._ensure_sources_came_from_web_search(urls)
        return urls

    def _latest_search_results(self) -> tuple[str, ...]:
        """The small model often leaves sources out; the search it just made is the source."""
        self._ensure_there_are_search_results()
        logger.info("No sources given: citing the results of the latest search")
        return self._seen_sources.latest_results

    def _ensure_there_are_search_results(self) -> None:
        if self._seen_sources.is_empty:
            raise ToolError(
                "you have no web_search results to cite in this conversation (you did not "
                "search yet, or the search found nothing): search with other words and cite "
                "the URLs it returns, or do not save anything this time"
            )

    def _ensure_sources_came_from_web_search(self, urls: tuple[str, ...]) -> None:
        self._ensure_there_are_search_results()
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


def _describe_drawing(pinned_drawing: PinnedDrawing) -> str:
    drawing = pinned_drawing.drawing
    description = (
        f"Then you walked to your chalkboard and drew it with {len(drawing.strokes)} chalk "
        f"stroke(s), saved as {pinned_drawing.file_name}."
    )
    if pinned_drawing.erased is not None:
        description += f" To make room, you erased the old drawing '{pinned_drawing.erased.title}'."
    return description
