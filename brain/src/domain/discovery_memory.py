from dataclasses import dataclass
from typing import Protocol

from src.domain.discovery import Discovery


@dataclass(frozen=True)
class RememberedDiscovery:
    """A discovery brought back from memory, with how close it is to what was asked.

    similarity is the cosine similarity: 1 means same meaning, 0 unrelated.
    """

    discovery: Discovery
    similarity: float


class DiscoveryMemoryError(Exception):
    """Raised when the memory cannot store or recall (database offline, embedder down...)."""


class DiscoveryMemory(Protocol):
    """Long-term memory: finds saved discoveries by meaning, not by exact words."""

    def remember(self, file_name: str, discovery: Discovery) -> None:
        """Stores the discovery. Remembering the same file_name again replaces it."""
        ...

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        """Up to `limit` discoveries closest in meaning to `text`, the most similar first."""
        ...


def memory_text(discovery: Discovery) -> str:
    """The part of a discovery that carries its meaning, which is what gets compared.

    Sources and date are left out: URLs would only add noise to the meaning.
    """
    return f"{discovery.title}\n{discovery.topic}\n{discovery.summary}"
