"""Stand-ins for everything around the model, so only the model's decisions vary in an eval.

The web always answers with the scenario's pages, and files stay in memory. The rules
(tools, inner voice, prompts) are the real ones used by the live capybara.
"""

from collections.abc import Sequence
from datetime import date

from src.domain.discovery import Discovery, DiscoveryHeadline
from src.domain.discovery_memory import RememberedDiscovery, memory_text
from src.domain.search_history import search_key
from src.domain.text_embedding import TextEmbedder, cosine_similarity
from src.domain.web_search import SearchResult
from src.domain.world_suggestion import SavedSuggestion, WorldSuggestion

PERFECT_SIMILARITY = 1.0


class ScriptedWebSearcher:
    """Returns the same pages for any query, and remembers which queries were asked."""

    def __init__(self, results: Sequence[SearchResult]) -> None:
        self._results = list(results)
        self.queries: list[str] = []

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        self.queries.append(query)
        return self._results[:max_results]


class InMemorySearchHistory:
    def __init__(self, earlier_queries: Sequence[str], searched_on: date) -> None:
        self._searched_on = {search_key(query): searched_on for query in earlier_queries}

    def last_searched_on(self, query: str) -> date | None:
        return self._searched_on.get(search_key(query))

    def record(self, query: str, searched_on: date) -> None:
        self._searched_on[search_key(query)] = searched_on


class InMemoryDiscoveries:
    """DiscoveryRepository and DiscoveryCatalog in one list, the newest last."""

    def __init__(self, known: Sequence[DiscoveryHeadline]) -> None:
        self._known = list(known)
        self.saved: list[Discovery] = []

    def save(self, discovery: Discovery) -> str:
        self.saved.append(discovery)
        return f"discovery-{len(self.saved)}.md"

    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        saved_headlines = [DiscoveryHeadline(item.title, item.topic) for item in self.saved]
        newest_first = list(reversed([*self._known, *saved_headlines]))
        return newest_first[:limit]


class FixedMemory:
    """DiscoveryMemory that always recalls the same discoveries, as perfect matches.

    The retrieval eval measures the real memory; here we only want to see what she does
    when related discoveries are in her context.
    """

    def __init__(self, discoveries: Sequence[Discovery]) -> None:
        self._discoveries = list(discoveries)

    def remember(self, file_name: str, discovery: Discovery) -> None:
        self._discoveries.append(discovery)

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        return [
            RememberedDiscovery(discovery, PERFECT_SIMILARITY)
            for discovery in self._discoveries[:limit]
        ]


class InMemorySuggestions:
    """WorldSuggestionRepository and WorldSuggestionArchive in one list, the oldest first."""

    def __init__(self, earlier: Sequence[WorldSuggestion]) -> None:
        self.suggestions = list(earlier)
        self._earlier_count = len(self.suggestions)

    @property
    def new_suggestions(self) -> list[WorldSuggestion]:
        return self.suggestions[self._earlier_count :]

    def save(self, suggestion: WorldSuggestion) -> str:
        self.suggestions.append(suggestion)
        return f"suggestion-{len(self.suggestions)}.md"

    def saved_suggestions(self) -> list[SavedSuggestion]:
        return [
            SavedSuggestion(f"suggestion-{position}.md", suggestion)
            for position, suggestion in enumerate(self.suggestions, start=1)
        ]


class EmbeddedMemory:
    """DiscoveryMemory kept in a list, compared with the real embedding model.

    Backs the recall_memory tool in the agent eval: what she finds depends on what she
    asks for, as in the real memory (but without the database).
    """

    def __init__(self, embedder: TextEmbedder, discoveries: Sequence[Discovery]) -> None:
        self._embedder = embedder
        self._discoveries = list(discoveries)

    def remember(self, file_name: str, discovery: Discovery) -> None:
        self._discoveries.append(discovery)

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        if not self._discoveries:
            return []
        query, *embeddings = self._embedder.embed(
            [text, *(memory_text(discovery) for discovery in self._discoveries)]
        )
        remembered = [
            RememberedDiscovery(discovery, cosine_similarity(query, embedding))
            for discovery, embedding in zip(self._discoveries, embeddings, strict=True)
        ]
        remembered.sort(key=lambda item: item.similarity, reverse=True)
        return remembered[:limit]
