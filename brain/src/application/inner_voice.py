import logging

from src.application.attention_inbox import AttentionInbox
from src.domain.attention import PointOfAttention
from src.domain.discovery import DiscoveryCatalog, DiscoveryHeadline, DiscoveryStorageError

DISCOVERIES_PLACEHOLDER = "{discoveries}"
NOTICED_PLACEHOLDER = "{noticed}"

logger = logging.getLogger(__name__)


class InnerVoice:
    """What the capybara tells herself at the start of each autonomous cycle.

    Every cycle is a fresh conversation, so she would forget what she already researched.
    Before the invitation to act, the inner voice lists her latest saved discoveries, so she
    picks something new (or a neighbouring subject) instead of searching the same thing again.

    When an attention inbox is given, it also lists the things she noticed in her world.
    After a cycle finishes, release_offered lets those things go: in that cycle she either
    researched one of them or decided they were not worth it, and both are a decision.
    """

    def __init__(
        self,
        invitation: str,
        catalog: DiscoveryCatalog,
        memory_template: str,
        max_remembered_discoveries: int,
        attention: AttentionInbox | None = None,
        noticed_template: str = "",
    ) -> None:
        self._invitation = invitation
        self._catalog = catalog
        self._memory_template = memory_template
        self._max_remembered_discoveries = max_remembered_discoveries
        self._attention = attention
        self._noticed_template = noticed_template
        self._offered: tuple[PointOfAttention, ...] = ()

    def compose(self) -> str:
        """Memory first, then what she noticed, and the invitation last.

        The end of the message is the part the model follows best.
        """
        self._offered = self._attention.pending() if self._attention is not None else ()
        parts = [self._memory(), self._noticed(), self._invitation]
        return "\n\n".join(part for part in parts if part)

    def release_offered(self) -> None:
        """Lets go of what the last composed inner voice offered her."""
        if self._attention is None or not self._offered:
            return
        for point in self._offered:
            self._attention.let_go(point.thing_id)
        logger.info(
            "She thought about what she noticed: %s",
            ", ".join(point.thing_id for point in self._offered),
        )
        self._offered = ()

    def _memory(self) -> str:
        try:
            headlines = self._catalog.latest_headlines(self._max_remembered_discoveries)
        except DiscoveryStorageError as error:
            logger.warning("Could not remember the saved discoveries: %s", error)
            return ""
        if not headlines:
            return ""
        discovery_lines = "\n".join(self._format(headline) for headline in headlines)
        return self._memory_template.replace(DISCOVERIES_PLACEHOLDER, discovery_lines)

    def _noticed(self) -> str:
        if not self._offered:
            return ""
        noticed_lines = "\n".join(f"- {point.description}" for point in self._offered)
        return self._noticed_template.replace(NOTICED_PLACEHOLDER, noticed_lines)

    @staticmethod
    def _format(headline: DiscoveryHeadline) -> str:
        if not headline.topic:
            return f"- {headline.title}"
        return f"- {headline.title} (tema: {headline.topic})"
