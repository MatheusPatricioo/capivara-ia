"""The capybara's emotional life: every layer together, moved by time and by events.

Layers, from the slowest to the fastest: temperament (fixed), baseline (weeks), bond
(days), needs (hours), mood (hours) and emotions (minutes). Times are seconds from the
Unix epoch, passed in by the caller, so the rules stay pure and easy to test.
"""

import random
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from src.domain.feelings.appraisal import (
    APPRAISAL_RULES,
    EmotionalEvent,
    EventKind,
    Familiarity,
    Outcome,
    scaled_impulses,
)
from src.domain.feelings.baseline import Baseline
from src.domain.feelings.bond import Bond
from src.domain.feelings.contagion import is_in_a_good_tide, is_ruminating, spread
from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.ladders import (
    CAPYBARA_LADDERS,
    EmotionLadder,
    LadderPosition,
    Rung,
    felt_on,
    moved,
    roll_jitter,
)
from src.domain.feelings.mood import Mood
from src.domain.feelings.needs import Need, NeedRhythm, Needs
from src.domain.feelings.temperament import Temperament

SECONDS_PER_HOUR = 3600.0
SECONDS_PER_DAY = 86400.0
SLEEP_AFTER_HOURS = 1.0
"""A longer gap without any update means the brain was off: she was asleep."""
MAX_STEP_HOURS = 0.25
"""Long gaps are lived in small steps, so emotions, needs and rungs keep moving together."""
MAX_CATCH_UP_HOURS = 14 * 24.0
DAY_SPIRIT_RANGE = 0.1
"""Every new day she wakes up a little better or worse, at random."""
DEFAULT_IMPULSE_NOISE = 0.15
"""Each impulse lands between 85% and 115% of its size."""
COMFORTED_LEVEL = 0.7
COMFORTED_PACE = 0.85
"""Well cared for, the other needs empty a bit more slowly."""
SLEEP_COMFORT_PER_HOUR = 1 / 8
AUTONOMY_REFILL_HOURS = 48.0
"""With no wish waiting, the feeling of not being heard heals in about two days."""
FULL_WAIT_HOURS = 7 * 24.0
SUCCESS_STREAK_ENTHUSIASM = 0.08
MAX_STREAK_ENTHUSIASM = 0.4
FAILURE_STREAK_STING = 0.5
"""Each failure in a row makes the next one sting 50% more."""
HURT_BRAKE = 0.7
"""Hurt slows how much talking refills the bond: she warms up again over a few chats."""


@dataclass(frozen=True)
class EmotionalSnapshot:
    """Everything that changes in her emotional life, to save and load it."""

    emotions: EmotionalState
    needs: Needs
    mood: Mood
    baseline: Baseline
    bond: Bond
    last_updated_at: float
    ladder_positions: Mapping[Need, LadderPosition] = field(default_factory=dict)
    familiarity: Familiarity = field(default_factory=Familiarity)
    success_streak: int = 0
    failure_streak: int = 0
    pending_wishes: int = 0
    last_talked_at: float | None = None
    day_number: int = 0
    day_spirit: float = 0.0


class EmotionalLife:
    def __init__(
        self,
        snapshot: EmotionalSnapshot,
        temperament: Temperament | None = None,
        rhythm: NeedRhythm | None = None,
        ladders: Mapping[Need, EmotionLadder] = CAPYBARA_LADDERS,
        rng: random.Random | None = None,
        impulse_noise: float = DEFAULT_IMPULSE_NOISE,
    ) -> None:
        self._temperament = temperament or Temperament()
        self._rhythm = rhythm or NeedRhythm()
        self._ladders = ladders
        self._rng = rng or random.Random()
        self._impulse_noise = impulse_noise
        self._emotions = snapshot.emotions
        self._needs = snapshot.needs
        self._mood = snapshot.mood
        self._baseline = snapshot.baseline
        self._bond = snapshot.bond
        self._last_updated_at = snapshot.last_updated_at
        self._positions = dict(snapshot.ladder_positions)
        self._familiarity = snapshot.familiarity
        self._success_streak = snapshot.success_streak
        self._failure_streak = snapshot.failure_streak
        self._pending_wishes = snapshot.pending_wishes
        self._last_talked_at = snapshot.last_talked_at
        self._day_number = snapshot.day_number
        self._day_spirit = snapshot.day_spirit

    @staticmethod
    def newborn(now: float, temperament: Temperament | None = None) -> EmotionalSnapshot:
        """Her first moment: needs full, feeling her natural curious, happy self."""
        temperament = temperament or Temperament()
        return EmotionalSnapshot(
            emotions=EmotionalState(temperament.resting_levels(Baseline())),
            needs=Needs(),
            mood=Mood(valence=temperament.natural_mood()),
            baseline=Baseline(),
            bond=Bond(),
            last_updated_at=now,
            day_number=_day_number(now),
        )

    def snapshot(self) -> EmotionalSnapshot:
        return EmotionalSnapshot(
            emotions=self._emotions,
            needs=self._needs,
            mood=self._mood,
            baseline=self._baseline,
            bond=self._bond,
            last_updated_at=self._last_updated_at,
            ladder_positions=dict(self._positions),
            familiarity=self._familiarity,
            success_streak=self._success_streak,
            failure_streak=self._failure_streak,
            pending_wishes=self._pending_wishes,
            last_talked_at=self._last_talked_at,
            day_number=self._day_number,
            day_spirit=self._day_spirit,
        )

    @property
    def emotions(self) -> EmotionalState:
        return self._emotions

    @property
    def needs(self) -> Needs:
        return self._needs

    @property
    def mood(self) -> Mood:
        return self._mood

    @property
    def baseline(self) -> Baseline:
        return self._baseline

    @property
    def bond(self) -> Bond:
        return self._bond

    @property
    def pending_wishes(self) -> int:
        return self._pending_wishes

    @property
    def success_streak(self) -> int:
        return self._success_streak

    @property
    def failure_streak(self) -> int:
        return self._failure_streak

    @property
    def is_ruminating(self) -> bool:
        return is_ruminating(self._emotions, self._needs)

    @property
    def is_in_a_good_tide(self) -> bool:
        return is_in_a_good_tide(self._emotions)

    def rung(self, need: Need) -> Rung:
        return self._ladders[need].rungs[self._position(need).rung_index]

    def rung_index(self, need: Need) -> int:
        return self._position(need).rung_index

    def hours_since_talked(self, now: float) -> float | None:
        if self._last_talked_at is None:
            return None
        return max(0.0, now - self._last_talked_at) / SECONDS_PER_HOUR

    def notice_pending_wishes(self, count: int) -> None:
        """How many of her wishes are waiting to be built; while any wait, autonomy empties."""
        self._pending_wishes = max(0, count)

    def advance(self, now: float) -> None:
        """Lives through the time since the last update."""
        elapsed_hours = (now - self._last_updated_at) / SECONDS_PER_HOUR
        if elapsed_hours <= 0:
            return
        self._roll_day_spirit(now)
        asleep = elapsed_hours > SLEEP_AFTER_HOURS
        remaining = min(elapsed_hours, MAX_CATCH_UP_HOURS)
        while remaining > 0:
            step = min(MAX_STEP_HOURS, remaining)
            self._live_through(step, asleep)
            remaining -= step
        self._last_updated_at = now

    def experience(self, event: EmotionalEvent, now: float) -> None:
        """Something happened: she appraises it and her emotions and needs change."""
        self.advance(now)
        rule = APPRAISAL_RULES[event.kind]
        strength = self._familiarity.habituation(event.kind) if rule.habituates else 1.0
        impulses: defaultdict[Emotion, float] = defaultdict(float, rule.impulses)
        need_changes = dict(rule.need_changes)
        self._count_streaks(rule.outcome, impulses)
        if event.kind is EventKind.TALKED_WITH_MATHEUS:
            self._feel_reunion(now, impulses, need_changes)
        elif event.kind is EventKind.WISH_GRANTED:
            self._feel_wish_granted(event.waited_hours, impulses)
        elif event.kind is EventKind.WISH_MADE:
            self._pending_wishes += 1
        landed = scaled_impulses(impulses, self._temperament, self._mood, strength, self._noise)
        self._emotions = self._emotions.nudged(landed)
        self._needs = self._needs.changed(
            {
                need: change * strength if change > 0 else change
                for need, change in need_changes.items()
            }
        )
        self._familiarity = self._familiarity.after(event.kind)
        self._move_on_ladders()

    def _live_through(self, hours: float, asleep: bool) -> None:
        self._needs = self._needs.depleted(self._rhythm, hours, self._need_paces(asleep))
        self._needs = self._needs.changed(self._refills(hours, asleep))
        self._move_on_ladders()
        resting = self._temperament.resting_levels(self._baseline)
        state = self._emotions.decayed_towards(
            resting, hours, self._temperament.half_life_multipliers()
        )
        state = spread(state, self._needs, hours)
        for need in self._ladders:
            state = felt_on(self.rung(need), state, hours)
        self._emotions = state
        self._mood = self._mood.followed(state, hours, self._day_spirit)
        self._baseline = self._baseline.drifted(
            self._mood.valence, self._temperament.natural_mood(), hours
        )
        self._familiarity = self._familiarity.faded(hours)

    def _need_paces(self, asleep: bool) -> dict[Need, float]:
        paces = {
            Need.BOND: self._bond.missing_pace,
            Need.AUTONOMY: self._temperament.impatience_pace if self._pending_wishes else 0.0,
        }
        if self._needs.level(Need.COMFORT) >= COMFORTED_LEVEL:
            for need in (Need.BOND, Need.NOVELTY, Need.COMPETENCE):
                paces[need] = paces.get(need, 1.0) * COMFORTED_PACE
        if asleep:
            for need in (Need.NOVELTY, Need.COMPETENCE, Need.COMFORT):
                paces[need] = 0.0
        return paces

    def _refills(self, hours: float, asleep: bool) -> dict[Need, float]:
        refills: dict[Need, float] = {}
        if not self._pending_wishes:
            refills[Need.AUTONOMY] = hours / AUTONOMY_REFILL_HOURS
        if asleep:
            refills[Need.COMFORT] = hours * SLEEP_COMFORT_PER_HOUR
        return refills

    def _move_on_ladders(self) -> None:
        for need, ladder in self._ladders.items():
            self._positions[need] = moved(
                ladder, self._position(need), self._needs.level(need), self._roll_jitter
            )

    def _position(self, need: Need) -> LadderPosition:
        return self._positions.get(need, LadderPosition())

    def _count_streaks(self, outcome: Outcome, impulses: defaultdict[Emotion, float]) -> None:
        """Successes in a row build enthusiasm; failures in a row sting more each time."""
        if outcome is Outcome.SUCCESS:
            self._success_streak += 1
            self._failure_streak = 0
            impulses[Emotion.ENTHUSIASM] += min(
                SUCCESS_STREAK_ENTHUSIASM * self._success_streak, MAX_STREAK_ENTHUSIASM
            )
        elif outcome is Outcome.FAILURE:
            impulses[Emotion.FRUSTRATION] *= 1.0 + FAILURE_STREAK_STING * self._failure_streak
            self._failure_streak += 1
            self._success_streak = 0

    def _feel_reunion(
        self,
        now: float,
        impulses: defaultdict[Emotion, float],
        need_changes: dict[Need, float],
    ) -> None:
        absence_hours = self.hours_since_talked(now) or 0.0
        self._bond, reunion_feelings = self._bond.after_reunion(absence_hours)
        for emotion, amount in reunion_feelings.items():
            impulses[emotion] += amount
        hurt_brake = 1.0 - HURT_BRAKE * self._emotions.intensity(Emotion.HURT)
        need_changes[Need.BOND] = (
            need_changes.get(Need.BOND, 0.0) * self._bond.recovery_pace * hurt_brake
        )
        self._last_talked_at = now

    def _feel_wish_granted(
        self, waited_hours: float, impulses: defaultdict[Emotion, float]
    ) -> None:
        """The longer she waited, the bigger the joy and gratitude; the more she had lost
        hope, the bigger the relief."""
        waited = min(max(waited_hours, 0.0) / FULL_WAIT_HOURS, 1.0)
        impulses[Emotion.JOY] += 0.3 * waited
        impulses[Emotion.GRATITUDE] += 0.4 * waited
        impulses[Emotion.RELIEF] += max(
            self._emotions.intensity(Emotion.IMPATIENCE),
            self._emotions.intensity(Emotion.DISAPPOINTMENT),
            self._emotions.intensity(Emotion.RESIGNATION),
        )
        self._bond = self._bond.after_wish_granted()
        self._pending_wishes = max(0, self._pending_wishes - 1)

    def _roll_day_spirit(self, now: float) -> None:
        today = _day_number(now)
        if today != self._day_number:
            self._day_number = today
            self._day_spirit = self._rng.uniform(-DAY_SPIRIT_RANGE, DAY_SPIRIT_RANGE)

    def _roll_jitter(self) -> float:
        return roll_jitter(self._rng.uniform)

    def _noise(self) -> float:
        return self._rng.uniform(1.0 - self._impulse_noise, 1.0 + self._impulse_noise)


def _day_number(now: float) -> int:
    return int(now // SECONDS_PER_DAY)
