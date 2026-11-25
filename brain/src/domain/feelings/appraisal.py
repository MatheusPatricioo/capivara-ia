"""Appraisal: what each thing that happens means to her, as emotional impulses and needs.

The same event never lands the same way twice: temperament, mood, habituation and a
little noise all scale it before it touches her emotions.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from src.domain.feelings.emotion import Emotion, is_negative, is_positive
from src.domain.feelings.mood import Mood
from src.domain.feelings.needs import Need
from src.domain.feelings.temperament import Temperament

FAMILIARITY_HALF_LIFE_HOURS = 2.0
HABITUATION_PER_REPEAT = 0.5
"""The second time in a short while lands at 2/3 of the first, the third at half."""


class EventKind(StrEnum):
    TALKED_WITH_MATHEUS = "talked_with_matheus"
    SEARCH_FOUND_SOMETHING = "search_found_something"
    SEARCH_FOUND_NOTHING = "search_found_nothing"
    SEARCH_REPEATED = "search_repeated"
    SEARCH_FAILED = "search_failed"
    """The search itself broke (network, blocked engine): not her fault."""
    DISCOVERY_SAVED = "discovery_saved"
    WISH_MADE = "wish_made"
    WISH_GRANTED = "wish_granted"
    NOTICED_SOMETHING = "noticed_something"
    VISITED_COMFORT_PLACE = "visited_comfort_place"
    LETTER_ANSWERED = "letter_answered"
    """She read her creator's reply to one of her letters."""


@dataclass(frozen=True)
class EmotionalEvent:
    kind: EventKind
    waited_hours: float = 0.0
    """For a granted wish: how long ago she asked for it."""


class Outcome(StrEnum):
    """Whether an event counts in her streak of successes or of failures."""

    SUCCESS = "success"
    FAILURE = "failure"
    NEITHER = "neither"


@dataclass(frozen=True)
class AppraisalRule:
    impulses: Mapping[Emotion, float]
    need_changes: Mapping[Need, float] = field(default_factory=dict)
    habituates: bool = True
    """False for events that keep landing hard: failures sting more when repeated."""
    outcome: Outcome = Outcome.NEITHER


APPRAISAL_RULES: Mapping[EventKind, AppraisalRule] = {
    EventKind.TALKED_WITH_MATHEUS: AppraisalRule(
        {Emotion.LONELINESS: -0.5, Emotion.SADNESS: -0.2, Emotion.APATHY: -0.3},
        {Need.BOND: 0.2},
    ),
    EventKind.SEARCH_FOUND_SOMETHING: AppraisalRule(
        {Emotion.CURIOSITY: 0.25, Emotion.JOY: 0.1, Emotion.FRUSTRATION: -0.2},
        {Need.NOVELTY: 0.2, Need.COMPETENCE: 0.08},
        outcome=Outcome.SUCCESS,
    ),
    EventKind.SEARCH_FOUND_NOTHING: AppraisalRule(
        {Emotion.FRUSTRATION: 0.3, Emotion.DISAPPOINTMENT: 0.1},
        {Need.COMPETENCE: -0.12},
        habituates=False,
        outcome=Outcome.FAILURE,
    ),
    EventKind.SEARCH_REPEATED: AppraisalRule(
        {Emotion.BOREDOM: 0.25, Emotion.IRRITATION: 0.05},
        {Need.NOVELTY: -0.08},
        habituates=False,
    ),
    EventKind.SEARCH_FAILED: AppraisalRule(
        {Emotion.FRUSTRATION: 0.2, Emotion.IRRITATION: 0.15},
        {Need.COMPETENCE: -0.05},
        habituates=False,
    ),
    EventKind.DISCOVERY_SAVED: AppraisalRule(
        {
            Emotion.PRIDE: 0.45,
            Emotion.JOY: 0.3,
            Emotion.FRUSTRATION: -0.3,
            Emotion.INSECURITY: -0.2,
        },
        {Need.COMPETENCE: 0.25, Need.NOVELTY: 0.15},
        outcome=Outcome.SUCCESS,
    ),
    EventKind.WISH_MADE: AppraisalRule({Emotion.ENTHUSIASM: 0.2, Emotion.CURIOSITY: 0.1}),
    EventKind.WISH_GRANTED: AppraisalRule(
        {
            Emotion.SURPRISE: 0.5,
            Emotion.JOY: 0.5,
            Emotion.GRATITUDE: 0.4,
            Emotion.RESIGNATION: -0.6,
            Emotion.DISAPPOINTMENT: -0.6,
        },
        {Need.AUTONOMY: 1.0, Need.BOND: 0.15},
        habituates=False,
    ),
    EventKind.NOTICED_SOMETHING: AppraisalRule(
        {Emotion.CURIOSITY: 0.3, Emotion.SURPRISE: 0.3, Emotion.BOREDOM: -0.2},
        {Need.NOVELTY: 0.1},
    ),
    # Softer than talking (he is not there), but someone wrote back: joy and gratitude.
    EventKind.LETTER_ANSWERED: AppraisalRule(
        {
            Emotion.JOY: 0.35,
            Emotion.GRATITUDE: 0.3,
            Emotion.LONELINESS: -0.3,
            Emotion.SADNESS: -0.15,
        },
        {Need.BOND: 0.15},
    ),
    EventKind.VISITED_COMFORT_PLACE: AppraisalRule(
        {
            Emotion.SADNESS: -0.25,
            Emotion.FRUSTRATION: -0.3,
            Emotion.IRRITATION: -0.35,
            Emotion.LONELINESS: -0.1,
            Emotion.BOREDOM: -0.1,
            Emotion.JOY: 0.05,
        },
        {Need.COMFORT: 0.45},
    ),
}


@dataclass(frozen=True)
class Familiarity:
    """How used she is to each kind of event lately; it fades with time."""

    counts: Mapping[EventKind, float] = field(default_factory=dict)

    def habituation(self, kind: EventKind) -> float:
        """1.0 for something new, smaller the more it happened lately."""
        return 1.0 / (1.0 + HABITUATION_PER_REPEAT * self.counts.get(kind, 0.0))

    def after(self, kind: EventKind) -> "Familiarity":
        return Familiarity({**self.counts, kind: self.counts.get(kind, 0.0) + 1.0})

    def faded(self, elapsed_hours: float) -> "Familiarity":
        remaining_share = 0.5 ** (elapsed_hours / FAMILIARITY_HALF_LIFE_HOURS)
        return Familiarity({kind: count * remaining_share for kind, count in self.counts.items()})


def scaled_impulses(
    impulses: Mapping[Emotion, float],
    temperament: Temperament,
    mood: Mood,
    strength: float,
    noise: Callable[[], float],
) -> dict[Emotion, float]:
    """How hard each impulse really lands on her.

    Impulses that raise a bad emotion are scaled by sensitivity and a bad mood; the ones
    that raise a good emotion by cheerfulness and a good mood. Soothing impulses (negative)
    only by strength and noise.
    """
    landed: dict[Emotion, float] = {}
    for emotion, amount in impulses.items():
        factor = strength * noise()
        if amount > 0 and is_negative(emotion):
            factor *= temperament.negative_impact * mood.negative_impact
        elif amount > 0 and is_positive(emotion):
            factor *= temperament.positive_impact * mood.positive_impact
        landed[emotion] = amount * factor
    return landed
