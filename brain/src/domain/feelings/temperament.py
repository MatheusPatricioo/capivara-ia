from dataclasses import dataclass, fields

from src.domain.feelings.baseline import Baseline
from src.domain.feelings.emotion import Emotion, EmotionalState, is_negative

RESTING_CURIOSITY_SHARE = 0.5
RESTING_JOY_SHARE = 0.4
RESTING_SADNESS_PER_LOST_BASELINE = 0.4
"""A baseline pushed down by a bad phase leaves a little sadness even at rest."""


@dataclass(frozen=True)
class Temperament:
    """Who she is deep down. Every trait goes from 0 to 1.

    The defaults are the capybara: very curious and cheerful, fairly patient.
    """

    curiosity: float = 0.9
    cheerfulness: float = 0.8
    patience: float = 0.6
    sensitivity: float = 0.5
    """How hard bad things hit her."""
    resilience: float = 0.7
    """How fast bad feelings fade."""

    def __post_init__(self) -> None:
        for trait in fields(self):
            trait_value = getattr(self, trait.name)
            if not 0.0 <= trait_value <= 1.0:
                raise ValueError(f"{trait.name} must be between 0 and 1, got {trait_value}")

    def resting_levels(self, baseline: Baseline) -> dict[Emotion, float]:
        """Where her emotions settle when nothing happens: curious and happy by default.

        The baseline moves those levels up after a good phase and down after a bad one.
        """
        lift = 1.0 + baseline.shift
        return {
            Emotion.CURIOSITY: min(1.0, self.curiosity * RESTING_CURIOSITY_SHARE * lift),
            Emotion.JOY: min(1.0, self.cheerfulness * RESTING_JOY_SHARE * lift),
            Emotion.SADNESS: max(0.0, -baseline.shift) * RESTING_SADNESS_PER_LOST_BASELINE,
        }

    def natural_mood(self) -> float:
        """The valence of her resting feelings with a neutral baseline: her normal mood."""
        return EmotionalState(self.resting_levels(Baseline())).valence

    @property
    def negative_impact(self) -> float:
        """Multiplies bad impulses: 1.0 for a sensitivity of 0.5."""
        return 0.6 + 0.8 * self.sensitivity

    @property
    def positive_impact(self) -> float:
        """Multiplies good impulses: a cheerful capybara enjoys things more."""
        return 0.7 + 0.6 * self.cheerfulness

    @property
    def impatience_pace(self) -> float:
        """How fast waiting wears her down: 0.9 for a patience of 0.6."""
        return 1.5 - self.patience

    def half_life_multipliers(self) -> dict[Emotion, float]:
        """Resilience shortens how long bad emotions linger (0.8x for a resilience of 0.7)."""
        multiplier = 1.5 - self.resilience
        return {emotion: multiplier for emotion in Emotion if is_negative(emotion)}
