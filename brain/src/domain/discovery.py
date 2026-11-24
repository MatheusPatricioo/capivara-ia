from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class Discovery:
    title: str
    topic: str
    summary: str
    sources: tuple[str, ...]
    discovered_on: date


class DiscoveryStorageError(Exception):
    """Raised when a discovery cannot be stored (disk failure, unsafe location...)."""


class DiscoveryRepository(Protocol):
    def save(self, discovery: Discovery) -> str:
        """Stores the discovery and returns the name it was saved under."""
        ...


class DiscoveryArchive(Protocol):
    """Reads back, in full, the discoveries that were already saved."""

    def saved_file_names(self) -> list[str]:
        """Names of every saved discovery, the oldest first."""
        ...

    def read(self, file_name: str) -> Discovery:
        """The discovery saved under file_name.

        Raises DiscoveryStorageError when it cannot be read or is not a discovery.
        """
        ...


@dataclass(frozen=True)
class DiscoveryHeadline:
    """Just enough of a saved discovery to remind the capybara that she already knows it."""

    title: str
    topic: str


class DiscoveryCatalog(Protocol):
    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        """Returns up to `limit` saved discoveries, the most recent first."""
        ...
