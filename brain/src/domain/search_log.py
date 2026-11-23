from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class FoundPage:
    """A page a web search returned, as shown later on the capybara's computer."""

    title: str
    url: str


@dataclass(frozen=True)
class SearchRecord:
    """One web search the capybara did: when, what she typed and what came back."""

    searched_at: datetime
    query: str
    results: tuple[FoundPage, ...]


class SearchLogError(Exception):
    """Raised when a search cannot be written to the log (disk failure...)."""


class SearchLog(Protocol):
    def append(self, record: SearchRecord) -> None:
        """Adds the search at the end of the log, keeping every earlier one."""
        ...
