from dataclasses import dataclass

from src.domain.feelings.emotion import CALM_AROUSAL, EmotionalState

MOOD_HALF_LIFE_HOURS = 6.0
"""Mood follows emotions slowly: one bad search does not spoil the day."""
NEGATIVE_IMPACT_PER_VALENCE = 0.4
POSITIVE_IMPACT_PER_VALENCE = 0.3


@dataclass(frozen=True)
class Mood:
    """The background colour of her day: a slow average of what she has been feeling.

    It changes how she takes new things: in a good mood a failure hurts less, in a bad
    mood good news is enjoyed less.
    """

    valence: float = 0.4
    arousal: float = CALM_AROUSAL

    def __post_init__(self) -> None:
        if not -1.0 <= self.valence <= 1.0:
            raise ValueError(f"mood valence must be between -1 and 1, got {self.valence}")
        if not 0.0 <= self.arousal <= 1.0:
            raise ValueError(f"mood arousal must be between 0 and 1, got {self.arousal}")

    def followed(
        self, state: EmotionalState, elapsed_hours: float, day_spirit: float = 0.0
    ) -> "Mood":
        """Moves towards what she feels now. day_spirit is the small luck of the day."""
        remaining_share = 0.5 ** (elapsed_hours / MOOD_HALF_LIFE_HOURS)
        target_valence = max(-1.0, min(1.0, state.valence + day_spirit))
        return Mood(
            valence=target_valence + (self.valence - target_valence) * remaining_share,
            arousal=state.arousal + (self.arousal - state.arousal) * remaining_share,
        )

    @property
    def negative_impact(self) -> float:
        """Multiplies bad impulses: 0.84 in a good mood (0.4), 1.16 in a bad one (-0.4)."""
        return 1.0 - NEGATIVE_IMPACT_PER_VALENCE * self.valence

    @property
    def positive_impact(self) -> float:
        """Multiplies good impulses."""
        return 1.0 + POSITIVE_IMPACT_PER_VALENCE * self.valence
