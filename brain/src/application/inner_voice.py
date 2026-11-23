import logging

from src.domain.discovery import DiscoveryCatalog, DiscoveryHeadline, DiscoveryStorageError

DISCOVERIES_PLACEHOLDER = "{discoveries}"

logger = logging.getLogger(__name__)


class InnerVoice:
    """What the capybara tells herself at the start of each autonomous cycle.

    Every cycle is a fresh conversation, so she would forget what she already researched.
    Before the invitation to act, the inner voice lists her latest saved discoveries, so she
    picks something new (or a neighbouring subject) instead of searching the same thing again.
    """

    def __init__(
        self,
        invitation: str,
        catalog: DiscoveryCatalog,
        memory_template: str,
        max_remembered_discoveries: int,
    ) -> None:
        self._invitation = invitation
        self._catalog = catalog
        self._memory_template = memory_template
        self._max_remembered_discoveries = max_remembered_discoveries

    def compose(self) -> str:
        """The memory comes first and the invitation last, the part the model reads best."""
        memory = self._memory()
        if not memory:
            return self._invitation
        return f"{memory}\n\n{self._invitation}"

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

    @staticmethod
    def _format(headline: DiscoveryHeadline) -> str:
        if not headline.topic:
            return f"- {headline.title}"
        return f"- {headline.title} (tema: {headline.topic})"
