from dataclasses import dataclass

MAX_SHIFT = 0.5
"""A baseline never moves more than half of her temperament up or down."""
BASELINE_HALF_LIFE_HOURS = 72.0
"""Days, not hours: one bad afternoon does not change who she is, a bad week does a bit."""
MOOD_TO_SHIFT = 0.5
"""Only half of how far her mood is from normal moves the baseline."""


@dataclass(frozen=True)
class Baseline:
    """How far a long phase moved her 'normal' away from her temperament (-0.5 to 0.5).

    0 means she is her usual self. A long sad phase pushes it down, so even at rest she
    feels a bit less joy and curiosity; a long good phase pushes it up. It always drifts
    back when her mood returns to her natural one.
    """

    shift: float = 0.0

    def __post_init__(self) -> None:
        if not -MAX_SHIFT <= self.shift <= MAX_SHIFT:
            raise ValueError(f"baseline shift must be within ±{MAX_SHIFT}, got {self.shift}")

    def drifted(self, mood_valence: float, natural_mood: float, elapsed_hours: float) -> "Baseline":
        """Moves slowly towards how far her mood is from her natural mood."""
        distance = (mood_valence - natural_mood) * MOOD_TO_SHIFT
        target = max(-MAX_SHIFT, min(MAX_SHIFT, distance))
        remaining_share = 0.5 ** (elapsed_hours / BASELINE_HALF_LIFE_HOURS)
        return Baseline(target + (self.shift - target) * remaining_share)
