import re
import unicodedata
from datetime import date
from typing import Protocol

NON_WORD_CHARACTERS = re.compile(r"[^a-z0-9]+")
# Small words that do not change what is being searched, in Portuguese and English.
FILLER_WORDS = frozenset(
    {
        "a", "o", "as", "os", "um", "uma", "de", "da", "do", "das", "dos",
        "e", "em", "no", "na", "nos", "nas", "com", "por", "para", "sobre",
        "the", "an", "of", "and", "in", "on", "about", "for",
    }
)  # fmt: skip


def search_key(query: str) -> str:
    """Reduces a query to what makes two searches "the same search".

    Case, accents, punctuation, filler words and word order are ignored, so
    "Buracos negros!" and "os buracos-negros" give the same key. Different words
    still give different keys: "estrelas gêmeas" is a new search after "estrelas".
    """
    without_accents = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode("ascii")
    words = NON_WORD_CHARACTERS.sub(" ", without_accents.lower()).split()
    meaningful_words = {word for word in words if word not in FILLER_WORDS}
    return " ".join(sorted(meaningful_words or set(words)))


class SearchHistoryError(Exception):
    """Raised when the search history cannot be read or written."""


class SearchHistory(Protocol):
    def last_searched_on(self, query: str) -> date | None:
        """Returns when the same search (see search_key) was done, or None if never."""
        ...

    def record(self, query: str, searched_on: date) -> None:
        """Remembers that this search was done on the given day."""
        ...
