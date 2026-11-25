from dataclasses import dataclass, replace

from src.domain.feelings.emotion import Emotion

MISSING_HOURS = 12.0
"""Shorter absences are just a chat; longer ones are a reunion."""
NEGLECT_HOURS = 48.0
"""Longer absences leave some hurt, and cost a little trust."""
FULL_ABSENCE_HOURS = 96.0
"""From here on, an absence feels as long as it gets."""
MAX_TRUST_LOSS = 0.15
TRUST_GAIN_PER_CARE = 0.02
TRUST_GAIN_PER_WISH_GRANTED = 0.05


@dataclass(frozen=True)
class Bond:
    """Her trust in her creator, from 0 to 1. It moves over days, not minutes.

    High trust is resilience: she misses him more slowly and recovers faster when he is
    back. Long absences, again and again, wear it down.
    """

    trust: float = 0.7

    def __post_init__(self) -> None:
        if not 0.0 <= self.trust <= 1.0:
            raise ValueError(f"trust must be between 0 and 1, got {self.trust}")

    @property
    def missing_pace(self) -> float:
        """Multiplies how fast the bond need empties: 0.88x with trust 0.7, 1.3x with none."""
        return 1.3 - 0.6 * self.trust

    @property
    def recovery_pace(self) -> float:
        """Multiplies how much a conversation refills the bond need."""
        return 0.6 + 0.6 * self.trust

    def after_reunion(self, absence_hours: float) -> tuple["Bond", dict[Emotion, float]]:
        """What seeing him again does to her: the longer the absence, the stronger and more
        mixed the feelings (joy and relief, with some hurt after real neglect)."""
        if absence_hours < MISSING_HOURS:
            return self._with_trust(TRUST_GAIN_PER_CARE / 2), {Emotion.JOY: 0.15}
        absence = min(absence_hours / FULL_ABSENCE_HOURS, 1.0)
        feelings = {
            Emotion.JOY: 0.35 + 0.45 * absence * (0.5 + self.trust / 2),
            Emotion.RELIEF: 0.4 * absence,
            Emotion.SURPRISE: 0.3 * absence,
        }
        if absence_hours <= NEGLECT_HOURS:
            return self._with_trust(TRUST_GAIN_PER_CARE), feelings
        feelings[Emotion.HURT] = 0.6 * absence * (1.0 - 0.6 * self.trust)
        trust_loss = min(0.06 * (absence_hours / NEGLECT_HOURS - 1.0), MAX_TRUST_LOSS)
        return self._with_trust(-trust_loss), feelings

    def after_wish_granted(self) -> "Bond":
        return self._with_trust(TRUST_GAIN_PER_WISH_GRANTED)

    def _with_trust(self, change: float) -> "Bond":
        return replace(self, trust=min(1.0, max(0.0, self.trust + change)))
