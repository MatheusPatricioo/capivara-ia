class SavedDiscoveries:
    """Remembers the discoveries saved in this conversation and which ones already got a drawing."""

    def __init__(self) -> None:
        self._saved_titles: set[str] = set()
        self._drawn_titles: set[str] = set()

    def remember(self, title: str) -> None:
        self._saved_titles.add(self._normalize(title))

    def contains(self, title: str) -> bool:
        return self._normalize(title) in self._saved_titles

    def mark_drawn(self, title: str) -> None:
        self._drawn_titles.add(self._normalize(title))

    def was_drawn(self, title: str) -> bool:
        return self._normalize(title) in self._drawn_titles

    @staticmethod
    def _normalize(title: str) -> str:
        """Ignores case and surrounding spaces, so 'O Sol ' and 'o sol' are the same discovery."""
        return title.strip().casefold()
