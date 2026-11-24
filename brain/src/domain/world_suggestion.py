from dataclasses import dataclass
from datetime import date
from typing import Protocol

MAX_REQUEST_LENGTH = 120
"""A request is a short title, like "Um laguinho com vitórias-régias", not a paragraph."""


class InvalidSuggestionError(Exception):
    """Raised when a suggestion breaks a rule (blank request, no reason...)."""


class SuggestionStorageError(Exception):
    """Raised when a suggestion cannot be stored (disk failure, unsafe location...)."""


@dataclass(frozen=True)
class WorldSuggestion:
    """Something the capybara would like to have in her world, inspired by what she learned.

    She only suggests: the developer reads the suggestions and builds the ones that make
    sense in the Godot world, so nothing here changes the world by itself.
    """

    request: str
    reason: str
    inspired_by: str
    """Title of the discovery that gave her the idea."""
    suggested_on: date

    def __post_init__(self) -> None:
        if not self.request.strip():
            raise InvalidSuggestionError("a suggestion needs a request")
        if len(self.request) > MAX_REQUEST_LENGTH:
            raise InvalidSuggestionError(
                f"a request must fit in {MAX_REQUEST_LENGTH} characters, like a title"
            )
        if not self.reason.strip():
            raise InvalidSuggestionError(f"the suggestion '{self.request}' needs a reason")
        if not self.inspired_by.strip():
            raise InvalidSuggestionError(
                f"the suggestion '{self.request}' needs the discovery that inspired it"
            )


class WorldSuggestionRepository(Protocol):
    def save(self, suggestion: WorldSuggestion) -> str:
        """Stores the suggestion and returns the name it was saved under.

        Raises SuggestionStorageError when it cannot be stored.
        """
        ...
