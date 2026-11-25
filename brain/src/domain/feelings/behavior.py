"""How what she feels changes what she does (broaden and build).

Good feelings widen her: bolder subjects, a faster pace. Bad feelings narrow her: less
energy, fewer wishes, a need to take care of herself. These are tendencies offered to her,
never orders: she still decides.
"""

import random
from enum import StrEnum

from src.domain.body import Place
from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.feelings.needs import Need

TENDENCY_THRESHOLD = 0.45
MIN_CYCLE_PACE = 0.6
MAX_CYCLE_PACE = 2.0
LOW_COMFORT = 0.5
DOWNCAST_VALENCE = -0.2
SELF_CARE_CHANCE_WHEN_DOWNCAST = 0.5
SURPRISE_PLACE_CHANCE = 0.2
"""Sometimes she goes to an unexpected place, like anyone would."""
COMFORT_PLACES = (Place.POND, Place.FOOD_BOWL, Place.DOG_HOUSE)


class Tendency(StrEnum):
    EXPLORE_BOLDLY = "explore_boldly"
    CHANGE_SUBJECT = "change_subject"
    TRY_ANOTHER_WAY = "try_another_way"
    MISS_COMPANY = "miss_company"
    LOW_ENERGY = "low_energy"
    STOP_ASKING = "stop_asking"


_TENDENCY_SOURCES: tuple[tuple[Tendency, tuple[Emotion, ...]], ...] = (
    (Tendency.EXPLORE_BOLDLY, (Emotion.FLOW, Emotion.ENTHUSIASM)),
    (Tendency.CHANGE_SUBJECT, (Emotion.BOREDOM,)),
    (Tendency.TRY_ANOTHER_WAY, (Emotion.DETERMINATION,)),
    (Tendency.MISS_COMPANY, (Emotion.LONELINESS,)),
    (Tendency.LOW_ENERGY, (Emotion.APATHY, Emotion.SADNESS)),
    (Tendency.STOP_ASKING, (Emotion.RESIGNATION,)),
)


def tendencies(state: EmotionalState) -> tuple[Tendency, ...]:
    """What she feels like doing, in a fixed order, from the emotions strong enough."""
    return tuple(
        tendency
        for tendency, sources in _TENDENCY_SOURCES
        if max(state.intensity(emotion) for emotion in sources) >= TENDENCY_THRESHOLD
    )


def cycle_pace(state: EmotionalState) -> float:
    """Multiplies the time between two cycles: slower when down, faster in a good tide."""
    heaviness = max(state.intensity(Emotion.APATHY), 0.8 * state.intensity(Emotion.SADNESS))
    lightness = max(state.intensity(Emotion.FLOW), state.intensity(Emotion.ENTHUSIASM))
    pace = 1.0 + heaviness - 0.3 * lightness
    return max(MIN_CYCLE_PACE, min(MAX_CYCLE_PACE, pace))


def comfort_place(life: EmotionalLife, rng: random.Random) -> Place | None:
    """Where she goes to take care of herself, or None when she does not need to.

    Low comfort always sends her; feeling down sends her half of the time. Sadness and
    loneliness look for the dog house, boredom and irritation for the pond, plain
    tiredness for the food bowl.
    """
    needs_comfort = life.needs.level(Need.COMFORT) < LOW_COMFORT
    is_downcast = life.emotions.valence < DOWNCAST_VALENCE
    if not needs_comfort and not (is_downcast and rng.random() < SELF_CARE_CHANCE_WHEN_DOWNCAST):
        return None
    if rng.random() < SURPRISE_PLACE_CHANCE:
        return rng.choice(COMFORT_PLACES)
    return _place_for(life.emotions, needs_comfort)


def _place_for(state: EmotionalState, needs_comfort: bool) -> Place:
    gloom = max(
        state.intensity(Emotion.SADNESS),
        state.intensity(Emotion.LONELINESS),
        state.intensity(Emotion.HURT),
    )
    agitation = max(
        state.intensity(Emotion.BOREDOM),
        state.intensity(Emotion.IRRITATION),
        state.intensity(Emotion.FRUSTRATION),
    )
    if needs_comfort and max(gloom, agitation) < TENDENCY_THRESHOLD:
        return Place.FOOD_BOWL
    return Place.DOG_HOUSE if gloom >= agitation else Place.POND
