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
