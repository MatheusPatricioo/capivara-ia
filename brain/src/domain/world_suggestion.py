import re
from dataclasses import dataclass, replace
from datetime import date
from enum import Enum
from typing import Protocol

MAX_REQUEST_LENGTH = 120
"""A request is a short title, like "Um laguinho com vitórias-régias", not a paragraph."""
WORLD_THING_ID_PATTERN = re.compile(r"[a-z0-9_]+")
"""The same kind of id the world gives the things she notices, like "big_oak"."""


class InvalidSuggestionError(Exception):
    """Raised when a suggestion breaks a rule (blank request, no reason...)."""


class SuggestionStorageError(Exception):
    """Raised when a suggestion cannot be stored (disk failure, unsafe location...)."""


class SuggestionStatus(Enum):
    PENDING = "pendente"
    BUILT = "construída"


@dataclass(frozen=True)
class WorldSuggestion:
    """Something the capybara would like to have in her world, inspired by what she learned.

    She only suggests: the developer reads the suggestions and builds the ones that make
    sense in the Godot world, then marks them as built. Nothing here changes the world.
    """

    request: str
    reason: str
    inspired_by: str
    """Title of the discovery that gave her the idea."""
    suggested_on: date
    status: SuggestionStatus = SuggestionStatus.PENDING
    world_thing_id: str = ""
    """Id of the thing built in the world for it (optional), so she can recognize it there."""

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
        if self.world_thing_id and not WORLD_THING_ID_PATTERN.fullmatch(self.world_thing_id):
            raise InvalidSuggestionError(
                f"'{self.world_thing_id}' is not a world thing id: use lowercase letters, "
                "digits and underscores, like big_oak"
            )

    @property
    def is_built(self) -> bool:
        return self.status is SuggestionStatus.BUILT

    def built(self, world_thing_id: str = "") -> "WorldSuggestion":
        """The same suggestion, marked as built (and linked to a world thing, when given)."""
        return replace(self, status=SuggestionStatus.BUILT, world_thing_id=world_thing_id)


@dataclass(frozen=True)
class SavedSuggestion:
    """A suggestion read back from storage, with the name it was saved under."""

    file_name: str
    suggestion: WorldSuggestion


class WorldSuggestionRepository(Protocol):
    def save(self, suggestion: WorldSuggestion) -> str:
        """Stores the suggestion and returns the name it was saved under.

        Raises SuggestionStorageError when it cannot be stored.
        """
        ...


class WorldSuggestionArchive(Protocol):
    def saved_suggestions(self) -> list[SavedSuggestion]:
        """Every suggestion already saved, the oldest first.

        Files that cannot be read, or are not suggestions, are skipped.
        """
        ...
