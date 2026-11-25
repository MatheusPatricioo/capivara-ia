from collections.abc import Iterable
from urllib.parse import unquote


class SeenSources:
    """Remembers the URLs that web_search showed to the model in the current conversation."""

    def __init__(self) -> None:
        self._comparable_urls: set[str] = set()
        self._latest_results: tuple[str, ...] = ()

    def remember(self, urls: Iterable[str]) -> None:
        cleaned_urls = tuple(url.strip() for url in urls)
        self._comparable_urls.update(_comparable(url) for url in cleaned_urls)
        if cleaned_urls:
            self._latest_results = cleaned_urls

    def contains(self, url: str) -> bool:
        """The same link written encoded ("Sat%C3%A9lites") or not ("Satélites") matches."""
        return _comparable(url) in self._comparable_urls

    @property
    def latest_results(self) -> tuple[str, ...]:
        """The URLs of the most recent search that found something, as it returned them."""
        return self._latest_results

    @property
    def is_empty(self) -> bool:
        return not self._comparable_urls


def _comparable(url: str) -> str:
    return unquote(url.strip())
