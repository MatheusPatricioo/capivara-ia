import time
from collections.abc import Callable
from typing import Protocol

from src.application.feelings_narrator import describe_feelings
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.world_suggestion import WorldSuggestionArchive

FEELINGS_PLACEHOLDER = "{feelings}"


class HeartCheck(Protocol):
    def check_in(self, pending_wishes: int | None = None) -> EmotionalLife: ...


class FeelingsVoice:
    """The part of her inner voice that tells her how she feels, and why.

    Before telling, it checks in with her heart: the time since the last moment is lived
    and the wishes still waiting are counted, so the feelings are always up to date.
    """

    def __init__(
        self,
        heart: HeartCheck,
        template: str,
        suggestions: WorldSuggestionArchive | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._heart = heart
        self._template = template
        self._suggestions = suggestions
        self._clock = clock

    def compose(self) -> str:
        life = self._heart.check_in(self._pending_wishes())
        return self._template.replace(FEELINGS_PLACEHOLDER, describe_feelings(life, self._clock()))

    def _pending_wishes(self) -> int | None:
        if self._suggestions is None:
            return None
        return sum(
            1 for saved in self._suggestions.saved_suggestions() if not saved.suggestion.is_built
        )
