from collections.abc import Iterable


class SeenSources:
    """Remembers the URLs that web_search showed to the model in the current conversation."""

    def __init__(self) -> None:
        self._urls: set[str] = set()

    def remember(self, urls: Iterable[str]) -> None:
        self._urls.update(url.strip() for url in urls)

    def contains(self, url: str) -> bool:
        return url.strip() in self._urls

    @property
    def is_empty(self) -> bool:
        return not self._urls
