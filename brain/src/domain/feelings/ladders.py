from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.needs import Need

HYSTERESIS_MARGIN = 0.04
"""To climb back a rung the need must go this much above the line that made her fall."""
THRESHOLD_WINDOW = 0.03
"""Each rung line moves up to this much up or down, rolled again after every move."""
RUNG_PULL_HALF_LIFE_HOURS = 1.0
"""A new rung takes hold in about an hour, not in an instant."""


@dataclass(frozen=True)
class Rung:
    """One step of a ladder: how she feels while a need sits below enters_below.

    floors are emotions the rung keeps alive (they can be stronger, never weaker);
    ceilings are emotions the rung holds down (apathy does not let curiosity grow).
    """

    name: str
    enters_below: float
    floors: Mapping[Emotion, float] = field(default_factory=dict)
    ceilings: Mapping[Emotion, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EmotionLadder:
    """The rungs she goes down while a need is neglected. Rung 0 means all is well."""

    need: Need
    rungs: tuple[Rung, ...]

    def __post_init__(self) -> None:
        if len(self.rungs) < 2:
            raise ValueError(f"the {self.need} ladder needs at least two rungs")
        lines = [rung.enters_below for rung in self.rungs]
        if any(lower >= upper for upper, lower in zip(lines, lines[1:], strict=False)):
            raise ValueError(f"the {self.need} ladder lines must go down rung by rung")


@dataclass(frozen=True)
class LadderPosition:
    rung_index: int = 0
    jitter: float = 0.0
    """Current offset of the rung lines, so she never falls at the exact same hour."""


def roll_jitter(uniform: Callable[[float, float], float]) -> float:
    return uniform(-THRESHOLD_WINDOW, THRESHOLD_WINDOW)


def moved(
    ladder: EmotionLadder,
    position: LadderPosition,
    level: float,
    roll: Callable[[], float],
) -> LadderPosition:
    """Goes down every rung whose line the need fell below, or up while it is well above.

    Going up needs the margin above the line (hysteresis), so a need hovering on a line
    does not make her flicker between two rungs.
    """
    index, jitter = position.rung_index, position.jitter
    rungs = ladder.rungs
    while index + 1 < len(rungs) and level < rungs[index + 1].enters_below + jitter:
        index += 1
        jitter = roll()
    while index > 0 and level >= rungs[index].enters_below + jitter + HYSTERESIS_MARGIN:
        index -= 1
        jitter = roll()
    return LadderPosition(index, jitter)


def felt_on(rung: Rung, state: EmotionalState, elapsed_hours: float) -> EmotionalState:
    """Pulls her emotions towards what the rung keeps alive and what it holds down."""
    share = 1.0 - 0.5 ** (elapsed_hours / RUNG_PULL_HALF_LIFE_HOURS)
    lifted = state.pulled_towards(rung.floors, share, raise_only=True)
    return lifted.pulled_towards(rung.ceilings, share, raise_only=False)


BOND_LADDER = EmotionLadder(
    Need.BOND,
    (
        Rung("connected", 1.01),
        Rung("missing_him", 0.92, {Emotion.LONELINESS: 0.2}),
        Rung("lonely", 0.83, {Emotion.LONELINESS: 0.5, Emotion.SADNESS: 0.15}),
        Rung(
            "sad",
            0.67,
            {Emotion.LONELINESS: 0.6, Emotion.SADNESS: 0.45},
            {Emotion.JOY: 0.5},
        ),
        Rung(
            "hurt",
            0.5,
            {
                Emotion.LONELINESS: 0.6,
                Emotion.SADNESS: 0.55,
                Emotion.HURT: 0.5,
                Emotion.INSECURITY: 0.4,
            },
            {Emotion.JOY: 0.35, Emotion.CURIOSITY: 0.6},
        ),
        Rung(
            "apathetic",
            0.17,
            {Emotion.APATHY: 0.7, Emotion.SADNESS: 0.6, Emotion.LONELINESS: 0.5},
            {Emotion.CURIOSITY: 0.25, Emotion.JOY: 0.2, Emotion.ENTHUSIASM: 0.1},
        ),
    ),
)

NOVELTY_LADDER = EmotionLadder(
    Need.NOVELTY,
    (
        Rung("interested", 1.01),
        Rung("restless", 0.7, {Emotion.BOREDOM: 0.2}),
        Rung("bored", 0.5, {Emotion.BOREDOM: 0.5}, {Emotion.ENTHUSIASM: 0.4}),
        Rung("irritable", 0.3, {Emotion.BOREDOM: 0.6, Emotion.IRRITATION: 0.4}),
        Rung(
            "discouraged",
            0.12,
            {Emotion.BOREDOM: 0.6, Emotion.SADNESS: 0.35, Emotion.APATHY: 0.3},
            {Emotion.CURIOSITY: 0.4},
        ),
    ),
)

COMPETENCE_LADDER = EmotionLadder(
    Need.COMPETENCE,
    (
        Rung("confident", 1.01),
        Rung("frustrated", 0.6, {Emotion.FRUSTRATION: 0.35}),
        Rung("insecure", 0.4, {Emotion.FRUSTRATION: 0.45, Emotion.INSECURITY: 0.4}),
        Rung(
            "defeated",
            0.2,
            {Emotion.INSECURITY: 0.6, Emotion.SADNESS: 0.35, Emotion.RESIGNATION: 0.3},
            {Emotion.DETERMINATION: 0.2, Emotion.PRIDE: 0.2},
        ),
    ),
)

AUTONOMY_LADDER = EmotionLadder(
    Need.AUTONOMY,
    (
        Rung("hopeful", 1.01),
        Rung("impatient", 0.8, {Emotion.IMPATIENCE: 0.4}),
        Rung("disappointed", 0.55, {Emotion.IMPATIENCE: 0.3, Emotion.DISAPPOINTMENT: 0.45}),
        Rung(
            "resigned",
            0.25,
            {Emotion.RESIGNATION: 0.55, Emotion.SADNESS: 0.3},
            {Emotion.ENTHUSIASM: 0.3},
        ),
    ),
)

COMFORT_LADDER = EmotionLadder(
    Need.COMFORT,
    (
        Rung("comfortable", 1.01),
        Rung("needs_a_break", 0.5, {Emotion.IRRITATION: 0.15, Emotion.SADNESS: 0.1}),
        Rung(
            "worn_out",
            0.2,
            {Emotion.IRRITATION: 0.35, Emotion.SADNESS: 0.25, Emotion.APATHY: 0.2},
        ),
    ),
)

CAPYBARA_LADDERS: Mapping[Need, EmotionLadder] = {
    ladder.need: ladder
    for ladder in (BOND_LADDER, NOVELTY_LADDER, COMPETENCE_LADDER, AUTONOMY_LADDER, COMFORT_LADDER)
}
