from datetime import date

from src.domain.world_suggestion import SavedSuggestion, WorldSuggestion

SUGGESTED_ON = date(2026, 11, 24)


def a_suggestion(request: str) -> WorldSuggestion:
    """A valid pending suggestion: only the request matters to most tests."""
    return WorldSuggestion(
        request=request,
        reason="Porque aprendi uma coisa linda.",
        inspired_by="Uma descoberta",
        suggested_on=SUGGESTED_ON,
    )


class InMemorySuggestionArchive:
    """WorldSuggestionArchive (and repository) kept in a list, the oldest first."""

    def __init__(self, suggestions: list[WorldSuggestion] | None = None) -> None:
        self.suggestions: list[WorldSuggestion] = list(suggestions or [])

    def save(self, suggestion: WorldSuggestion) -> str:
        self.suggestions.append(suggestion)
        return f"suggestion-{len(self.suggestions)}.md"

    def saved_suggestions(self) -> list[SavedSuggestion]:
        return [
            SavedSuggestion(f"suggestion-{position}.md", suggestion)
            for position, suggestion in enumerate(self.suggestions, start=1)
        ]
