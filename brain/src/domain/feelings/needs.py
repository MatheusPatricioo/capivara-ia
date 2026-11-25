from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class Need(StrEnum):
    """What she needs to stay her curious, happy self (self-determination theory + novelty)."""

    BOND = "bond"
    """Talking with Matheus."""
    NOVELTY = "novelty"
    """Learning new things."""
    COMPETENCE = "competence"
    """Getting right what she tries. Mostly moved by successes and failures, barely by time."""
    AUTONOMY = "autonomy"
    """Being heard: her wishes for the world get built."""
    COMFORT = "comfort"
    """Taking care of herself: the pond, the food bowl, the dog house."""


DEFAULT_HOURS_TO_EMPTY: Mapping[Need, float] = {
    Need.BOND: 144.0,
    Need.NOVELTY: 30.0,
    Need.COMPETENCE: 240.0,
    Need.AUTONOMY: 240.0,
    Need.COMFORT: 40.0,
}


@dataclass(frozen=True)
class NeedRhythm:
    """How many hours each need takes to empty from full when nothing refills it.

    time_scale speeds everything up (2.0 = twice as fast), handy to watch her live.
    """

    hours_to_empty: Mapping[Need, float] = field(
        default_factory=lambda: dict(DEFAULT_HOURS_TO_EMPTY)
    )
    time_scale: float = 1.0

    def __post_init__(self) -> None:
        if self.time_scale <= 0:
            raise ValueError(f"time_scale must be positive, got {self.time_scale}")
        for need in Need:
            hours = self.hours_to_empty.get(need)
            if hours is None or hours <= 0:
                raise ValueError(f"{need} needs a positive number of hours to empty")

    def depletion_per_hour(self, need: Need) -> float:
        return self.time_scale / self.hours_to_empty[need]


@dataclass(frozen=True)
class Needs:
    """How full each need is, from 0 (empty) to 1 (satisfied). A missing need is full."""

    levels: Mapping[Need, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for need, level in self.levels.items():
            if not 0.0 <= level <= 1.0:
                raise ValueError(f"{need} level must be between 0 and 1, got {level}")

    def level(self, need: Need) -> float:
        return self.levels.get(need, 1.0)

    def depleted(
        self,
        rhythm: NeedRhythm,
        elapsed_hours: float,
        multipliers: Mapping[Need, float] | None = None,
    ) -> "Needs":
        """Every need empties with time.

        A multiplier of 0 freezes a need, 2 empties it twice as fast.
        """
        paces = multipliers or {}
        return self.changed(
            {
                need: -rhythm.depletion_per_hour(need) * elapsed_hours * paces.get(need, 1.0)
                for need in Need
            }
        )

    def changed(self, changes: Mapping[Need, float]) -> "Needs":
        """Adds (or removes, when negative) to each need, kept between 0 and 1."""
        levels = dict(self.levels)
        for need, amount in changes.items():
            levels[need] = min(1.0, max(0.0, self.level(need) + amount))
        return Needs(levels)

    def most_unmet(self) -> Need:
        return min(Need, key=self.level)
