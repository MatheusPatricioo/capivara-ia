import random
from collections.abc import Mapping

from src.domain.feelings.baseline import Baseline
from src.domain.feelings.bond import Bond
from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.emotional_life import EmotionalLife, EmotionalSnapshot
from src.domain.feelings.ladders import LadderPosition
from src.domain.feelings.mood import Mood
from src.domain.feelings.needs import Need, Needs

NOW = 1_800_000_000.0
SECONDS_PER_HOUR = 3600.0


class AlwaysRandom(random.Random):
    """random() always returns the same number, so every chance is decided in advance."""

    def __init__(self, value: float) -> None:
        super().__init__(0)
        self._value = value

    def random(self) -> float:
        return self._value


def a_life(
    emotions: Mapping[Emotion, float] | None = None,
    needs: Mapping[Need, float] | None = None,
    rungs: Mapping[Need, int] | None = None,
    hours_since_talked: float | None = None,
) -> EmotionalLife:
    """An emotional life frozen at NOW in exactly the state a test needs."""
    last_talked_at = (
        None if hours_since_talked is None else NOW - hours_since_talked * SECONDS_PER_HOUR
    )
    return EmotionalLife(
        EmotionalSnapshot(
            emotions=EmotionalState(dict(emotions or {})),
            needs=Needs(dict(needs or {})),
            mood=Mood(),
            baseline=Baseline(),
            bond=Bond(),
            last_updated_at=NOW,
            ladder_positions={need: LadderPosition(index) for need, index in (rungs or {}).items()},
            last_talked_at=last_talked_at,
        )
    )
