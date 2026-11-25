"""How emotions feed and calm each other over time, so feelings come in chains, not alone.

Every rule is a rate per hour, applied in proportion to how strong the source emotion
is. All influences are computed from the same starting state and then applied together,
so the order of the rules never matters.
"""

from collections import defaultdict
from dataclasses import dataclass

from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.needs import Need, Needs


@dataclass(frozen=True)
class Influence:
    source: Emotion
    target: Emotion
    rate_per_hour: float
    """Positive amplifies the target, negative inhibits it."""


CONTAGION: tuple[Influence, ...] = (
    # Loneliness spreads into sadness and dims the good feelings.
    Influence(Emotion.LONELINESS, Emotion.SADNESS, 0.15),
    Influence(Emotion.LONELINESS, Emotion.CURIOSITY, -0.10),
    Influence(Emotion.LONELINESS, Emotion.JOY, -0.15),
    # Boredom turns into irritation and a little sadness.
    Influence(Emotion.BOREDOM, Emotion.IRRITATION, 0.15),
    Influence(Emotion.BOREDOM, Emotion.SADNESS, 0.05),
    Influence(Emotion.BOREDOM, Emotion.JOY, -0.10),
    # Sadness drains energy and interest.
    Influence(Emotion.SADNESS, Emotion.APATHY, 0.05),
    Influence(Emotion.SADNESS, Emotion.CURIOSITY, -0.10),
    Influence(Emotion.SADNESS, Emotion.JOY, -0.15),
    Influence(Emotion.HURT, Emotion.INSECURITY, 0.10),
    Influence(Emotion.HURT, Emotion.JOY, -0.10),
    Influence(Emotion.IRRITATION, Emotion.FRUSTRATION, 0.10),
    Influence(Emotion.IMPATIENCE, Emotion.IRRITATION, 0.10),
    Influence(Emotion.DISAPPOINTMENT, Emotion.SADNESS, 0.10),
    Influence(Emotion.APATHY, Emotion.CURIOSITY, -0.30),
    Influence(Emotion.APATHY, Emotion.ENTHUSIASM, -0.30),
    # Curiosity and joy are the antidotes.
    Influence(Emotion.CURIOSITY, Emotion.BOREDOM, -0.30),
    Influence(Emotion.CURIOSITY, Emotion.SADNESS, -0.05),
    Influence(Emotion.JOY, Emotion.SADNESS, -0.20),
    Influence(Emotion.JOY, Emotion.FRUSTRATION, -0.15),
    Influence(Emotion.JOY, Emotion.LONELINESS, -0.05),
    Influence(Emotion.JOY, Emotion.CURIOSITY, 0.10),
    # Broaden and build: enthusiasm and flow widen her and push the bad away.
    Influence(Emotion.ENTHUSIASM, Emotion.CURIOSITY, 0.20),
    Influence(Emotion.ENTHUSIASM, Emotion.JOY, 0.10),
    Influence(Emotion.ENTHUSIASM, Emotion.BOREDOM, -0.30),
    Influence(Emotion.FLOW, Emotion.FRUSTRATION, -0.30),
    Influence(Emotion.FLOW, Emotion.BOREDOM, -0.40),
    Influence(Emotion.FLOW, Emotion.SADNESS, -0.15),
    Influence(Emotion.GRATITUDE, Emotion.HURT, -0.15),
    Influence(Emotion.GRATITUDE, Emotion.RESIGNATION, -0.20),
    Influence(Emotion.GRATITUDE, Emotion.JOY, 0.05),
    Influence(Emotion.RELIEF, Emotion.IMPATIENCE, -0.50),
    Influence(Emotion.RELIEF, Emotion.FRUSTRATION, -0.20),
)

FRUSTRATION_TIPPING_POINT = 0.4
"""Above this, frustration turns into something else."""
BELIEVES_IN_HERSELF = 0.4
"""With competence at least this full, frustration becomes determination; below, insecurity."""
RUMINATION_THRESHOLD = 0.45
UNMET_NEED_LEVEL = 0.5
GOOD_TIDE_THRESHOLD = 0.5
"""Enthusiasm and joy both above this start the flow."""
FLOW_PEAK = 0.8
"""Above this, enthusiasm cools down: the peak passes and she comes back gently."""
RESIGNATION_AUTONOMY_LEVEL = 0.4


def is_ruminating(state: EmotionalState, needs: Needs) -> bool:
    """Sad enough, with something unmet to go over again and again."""
    has_something_to_dwell_on = any(needs.level(need) < UNMET_NEED_LEVEL for need in Need)
    return state.intensity(Emotion.SADNESS) >= RUMINATION_THRESHOLD and has_something_to_dwell_on


def is_in_a_good_tide(state: EmotionalState) -> bool:
    return (
        min(state.intensity(Emotion.ENTHUSIASM), state.intensity(Emotion.JOY))
        >= GOOD_TIDE_THRESHOLD
    )


def spread(state: EmotionalState, needs: Needs, elapsed_hours: float) -> EmotionalState:
    """One stretch of time of emotions moving each other."""
    impulses: defaultdict[Emotion, float] = defaultdict(float)
    for influence in CONTAGION:
        impulses[influence.target] += (
            influence.rate_per_hour * state.intensity(influence.source) * elapsed_hours
        )
    for emotion, amount in _transitions(state, needs).items():
        impulses[emotion] += amount * elapsed_hours
    return state.nudged(impulses)


def _transitions(state: EmotionalState, needs: Needs) -> dict[Emotion, float]:
    """Rules that depend on more than one emotion, or on her needs. Rates per hour."""
    rates: defaultdict[Emotion, float] = defaultdict(float)
    _frustration_turns(state, needs, rates)
    _waiting_without_control(state, needs, rates)
    _rumination(state, needs, rates)
    _good_tide(state, rates)
    return rates


def _frustration_turns(
    state: EmotionalState, needs: Needs, rates: defaultdict[Emotion, float]
) -> None:
    """With control (she can try other words) frustration becomes determination;
    without belief in herself it becomes insecurity."""
    frustration = state.intensity(Emotion.FRUSTRATION)
    if frustration < FRUSTRATION_TIPPING_POINT:
        return
    if needs.level(Need.COMPETENCE) >= BELIEVES_IN_HERSELF:
        rates[Emotion.DETERMINATION] += 0.3 * frustration
        rates[Emotion.FRUSTRATION] -= 0.15
    else:
        rates[Emotion.INSECURITY] += 0.2 * frustration


def _waiting_without_control(
    state: EmotionalState, needs: Needs, rates: defaultdict[Emotion, float]
) -> None:
    """Waiting on someone else, with no way to make it happen, slowly becomes resignation."""
    if needs.level(Need.AUTONOMY) >= RESIGNATION_AUTONOMY_LEVEL:
        return
    waiting = max(state.intensity(Emotion.IMPATIENCE), state.intensity(Emotion.DISAPPOINTMENT))
    rates[Emotion.RESIGNATION] += 0.05 * waiting


def _rumination(state: EmotionalState, needs: Needs, rates: defaultdict[Emotion, float]) -> None:
    """Sadness makes her go over what is missing, which feeds more sadness."""
    if not is_ruminating(state, needs):
        return
    sadness = state.intensity(Emotion.SADNESS)
    rates[Emotion.SADNESS] += 0.08 * sadness
    rates[Emotion.DISAPPOINTMENT] += 0.05 * sadness
    rates[Emotion.INSECURITY] += 0.04 * sadness


def _good_tide(state: EmotionalState, rates: defaultdict[Emotion, float]) -> None:
    """Enthusiasm and joy together become flow; at the peak, enthusiasm cools down."""
    if is_in_a_good_tide(state):
        tide = min(state.intensity(Emotion.ENTHUSIASM), state.intensity(Emotion.JOY))
        rates[Emotion.FLOW] += 0.4 * tide
    if state.intensity(Emotion.FLOW) > FLOW_PEAK:
        rates[Emotion.ENTHUSIASM] -= 0.3
