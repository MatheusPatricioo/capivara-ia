import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, StrEnum


class Emotion(StrEnum):
    JOY = "joy"
    CURIOSITY = "curiosity"
    ENTHUSIASM = "enthusiasm"
    FLOW = "flow"
    """The good tide: successes in a row, bold ideas, time flies."""
    PRIDE = "pride"
    GRATITUDE = "gratitude"
    RELIEF = "relief"
    DETERMINATION = "determination"
    SURPRISE = "surprise"
    LONELINESS = "loneliness"
    SADNESS = "sadness"
    HURT = "hurt"
    INSECURITY = "insecurity"
    APATHY = "apathy"
    BOREDOM = "boredom"
    IRRITATION = "irritation"
    FRUSTRATION = "frustration"
    IMPATIENCE = "impatience"
    DISAPPOINTMENT = "disappointment"
    RESIGNATION = "resignation"


class Valence(Enum):
    """Whether an emotion feels good, bad or neither."""

    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1


@dataclass(frozen=True)
class EmotionProfile:
    valence: Valence
    arousal: float
    """How agitated the emotion makes her, from 0 (calm) to 1 (restless)."""
    half_life_hours: float
    """Time for the emotion to fade halfway back to its resting level."""


EMOTION_PROFILES: Mapping[Emotion, EmotionProfile] = {
    Emotion.JOY: EmotionProfile(Valence.POSITIVE, 0.6, 2.0),
    Emotion.CURIOSITY: EmotionProfile(Valence.POSITIVE, 0.6, 3.0),
    Emotion.ENTHUSIASM: EmotionProfile(Valence.POSITIVE, 0.8, 3.0),
    Emotion.FLOW: EmotionProfile(Valence.POSITIVE, 0.7, 1.5),
    Emotion.PRIDE: EmotionProfile(Valence.POSITIVE, 0.5, 6.0),
    Emotion.GRATITUDE: EmotionProfile(Valence.POSITIVE, 0.4, 24.0),
    Emotion.RELIEF: EmotionProfile(Valence.POSITIVE, 0.3, 3.0),
    Emotion.DETERMINATION: EmotionProfile(Valence.POSITIVE, 0.7, 2.0),
    Emotion.SURPRISE: EmotionProfile(Valence.NEUTRAL, 0.9, 0.1),
    Emotion.LONELINESS: EmotionProfile(Valence.NEGATIVE, 0.3, 12.0),
    Emotion.SADNESS: EmotionProfile(Valence.NEGATIVE, 0.2, 18.0),
    Emotion.HURT: EmotionProfile(Valence.NEGATIVE, 0.4, 30.0),
    Emotion.INSECURITY: EmotionProfile(Valence.NEGATIVE, 0.5, 24.0),
    Emotion.APATHY: EmotionProfile(Valence.NEGATIVE, 0.05, 24.0),
    Emotion.BOREDOM: EmotionProfile(Valence.NEGATIVE, 0.2, 4.0),
    Emotion.IRRITATION: EmotionProfile(Valence.NEGATIVE, 0.8, 2.0),
    Emotion.FRUSTRATION: EmotionProfile(Valence.NEGATIVE, 0.8, 3.0),
    Emotion.IMPATIENCE: EmotionProfile(Valence.NEGATIVE, 0.7, 8.0),
    Emotion.DISAPPOINTMENT: EmotionProfile(Valence.NEGATIVE, 0.4, 12.0),
    Emotion.RESIGNATION: EmotionProfile(Valence.NEGATIVE, 0.1, 48.0),
}

CALM_AROUSAL = 0.3
"""Arousal of a capybara feeling nothing in particular."""


def is_positive(emotion: Emotion) -> bool:
    return EMOTION_PROFILES[emotion].valence is Valence.POSITIVE


def is_negative(emotion: Emotion) -> bool:
    return EMOTION_PROFILES[emotion].valence is Valence.NEGATIVE


def _clamped(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _saturating_sum(intensity: float, amount: float) -> float:
    """Adds an impulse that never overflows: the closer to the edge, the smaller the step.

    +0.5 on 0.0 gives 0.5, on 0.8 gives 0.9. -0.5 on 0.8 gives 0.4.
    """
    amount = max(-1.0, min(1.0, amount))
    if amount >= 0:
        return intensity + amount * (1.0 - intensity)
    return intensity + amount * intensity


def _faded(value: float, resting: float, elapsed_hours: float, half_life_hours: float) -> float:
    """Exponential decay towards the resting level: half the distance per half-life."""
    remaining_share = math.pow(0.5, elapsed_hours / half_life_hours)
    return resting + (value - resting) * remaining_share


@dataclass(frozen=True)
class EmotionalState:
    """How strong each emotion is right now, from 0 (absent) to 1 (overwhelming).

    Immutable: every change returns a new state. A missing emotion has intensity 0.
    """

    intensities: Mapping[Emotion, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for emotion, intensity in self.intensities.items():
            if not 0.0 <= intensity <= 1.0:
                raise ValueError(f"{emotion} intensity must be between 0 and 1, got {intensity}")

    def intensity(self, emotion: Emotion) -> float:
        return self.intensities.get(emotion, 0.0)

    def nudged(self, impulses: Mapping[Emotion, float]) -> "EmotionalState":
        """Positive impulses strengthen an emotion, negative ones soothe it (-1 to 1)."""
        changed = dict(self.intensities)
        for emotion, amount in impulses.items():
            changed[emotion] = _clamped(_saturating_sum(self.intensity(emotion), amount))
        return EmotionalState(changed)

    def pulled_towards(
        self, targets: Mapping[Emotion, float], share: float, raise_only: bool
    ) -> "EmotionalState":
        """Moves each emotion a share of the way to its target.

        raise_only=True only lifts emotions below the target (a floor); False only lowers
        emotions above it (a ceiling).
        """
        changed = dict(self.intensities)
        for emotion, target in targets.items():
            current = self.intensity(emotion)
            is_on_the_right_side = current >= target if raise_only else current <= target
            if not is_on_the_right_side:
                changed[emotion] = _clamped(current + (target - current) * share)
        return EmotionalState(changed)

    def decayed_towards(
        self,
        resting_levels: Mapping[Emotion, float],
        elapsed_hours: float,
        half_life_multipliers: Mapping[Emotion, float] | None = None,
    ) -> "EmotionalState":
        """Every emotion fades towards its resting level (0 when not given)."""
        multipliers = half_life_multipliers or {}
        emotions = set(self.intensities) | set(resting_levels)
        return EmotionalState(
            {
                emotion: _clamped(
                    _faded(
                        self.intensity(emotion),
                        resting_levels.get(emotion, 0.0),
                        elapsed_hours,
                        EMOTION_PROFILES[emotion].half_life_hours * multipliers.get(emotion, 1.0),
                    )
                )
                for emotion in emotions
            }
        )

    def strongest(self, limit: int, minimum: float = 0.0) -> tuple[tuple[Emotion, float], ...]:
        """The strongest emotions above minimum, strongest first."""
        felt = [
            (emotion, intensity)
            for emotion, intensity in self.intensities.items()
            if intensity > minimum
        ]
        felt.sort(key=lambda pair: (-pair[1], pair[0].value))
        return tuple(felt[:limit])

    @property
    def valence(self) -> float:
        """From -1 (all bad) to 1 (all good). The +1 keeps faint feelings near neutral."""
        positive = sum(self.intensity(emotion) for emotion in Emotion if is_positive(emotion))
        negative = sum(self.intensity(emotion) for emotion in Emotion if is_negative(emotion))
        return (positive - negative) / (positive + negative + 1.0)

    @property
    def arousal(self) -> float:
        """Average agitation of what she feels, weighted by intensity."""
        total = sum(self.intensities.values())
        if total == 0:
            return CALM_AROUSAL
        weighted = sum(
            intensity * EMOTION_PROFILES[emotion].arousal
            for emotion, intensity in self.intensities.items()
        )
        return weighted / total
