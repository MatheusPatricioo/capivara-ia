import random

import pytest

from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.emotional_life import SECONDS_PER_HOUR, EmotionalLife
from src.domain.feelings.ladders import BOND_LADDER
from src.domain.feelings.needs import Need
from src.domain.feelings.temperament import Temperament

BORN_AT = 1_800_000_000.0
AWAKE_STEP_HOURS = 0.5
TWO_DAYS = 48.0
FOUR_DAYS = 96.0
A_WEEK = 168.0
HURT_RUNG = 4
APATHETIC_RUNG = 5


def at(hours: float) -> float:
    return BORN_AT + hours * SECONDS_PER_HOUR


def stay_awake(life: EmotionalLife, from_hours: float, to_hours: float) -> None:
    """Small steps, like the live loop checking on her every few minutes."""
    hours = from_hours
    while hours < to_hours:
        hours = min(hours + AWAKE_STEP_HOURS, to_hours)
        life.advance(at(hours))


def feel(life: EmotionalLife, kind: EventKind, hours: float, waited_hours: float = 0.0) -> None:
    life.experience(EmotionalEvent(kind, waited_hours), at(hours))


def create_life() -> EmotionalLife:
    return EmotionalLife(EmotionalLife.newborn(BORN_AT), rng=random.Random(7), impulse_noise=0.0)


@pytest.fixture
def life() -> EmotionalLife:
    return create_life()


@pytest.fixture
def neglected_life(life: EmotionalLife) -> EmotionalLife:
    """Talked with Matheus once, then four days alone."""
    feel(life, EventKind.TALKED_WITH_MATHEUS, 0.0)
    stay_awake(life, 0.0, FOUR_DAYS)
    return life


def test_she_is_born_curious_and_happy(life: EmotionalLife) -> None:
    strongest = {emotion for emotion, _ in life.emotions.strongest(limit=2)}

    assert strongest == {Emotion.CURIOSITY, Emotion.JOY}


def test_a_day_after_a_discovery_her_pride_has_faded(life: EmotionalLife) -> None:
    feel(life, EventKind.DISCOVERY_SAVED, 0.0)

    stay_awake(life, 0.0, 24.0)

    assert life.emotions.intensity(Emotion.PRIDE) < 0.1


def test_two_days_without_talking_make_her_lonely(life: EmotionalLife) -> None:
    feel(life, EventKind.TALKED_WITH_MATHEUS, 0.0)

    stay_awake(life, 0.0, TWO_DAYS)

    assert life.rung(Need.BOND).name == "lonely"


def test_a_week_without_talking_makes_her_apathetic(life: EmotionalLife) -> None:
    feel(life, EventKind.TALKED_WITH_MATHEUS, 0.0)

    stay_awake(life, 0.0, A_WEEK)

    assert life.rung_index(Need.BOND) == APATHETIC_RUNG


def test_loneliness_escalates_into_sadness(neglected_life: EmotionalLife) -> None:
    assert neglected_life.emotions.intensity(Emotion.SADNESS) > 0.3


def test_after_a_long_absence_his_return_brings_joy_and_hurt_together(
    neglected_life: EmotionalLife,
) -> None:
    feel(neglected_life, EventKind.TALKED_WITH_MATHEUS, FOUR_DAYS)

    assert neglected_life.emotions.intensity(Emotion.JOY) > 0.6
    assert neglected_life.emotions.intensity(Emotion.HURT) > 0.1


def test_a_short_chat_after_a_long_absence_climbs_but_not_to_the_top(
    neglected_life: EmotionalLife,
) -> None:
    rung_before = neglected_life.rung_index(Need.BOND)

    for message in range(3):
        feel(neglected_life, EventKind.TALKED_WITH_MATHEUS, FOUR_DAYS + 0.02 * message)

    assert 0 < neglected_life.rung_index(Need.BOND) < rung_before


def test_the_hurt_of_a_long_absence_slows_how_fast_talking_heals(
    neglected_life: EmotionalLife,
) -> None:
    feel(neglected_life, EventKind.TALKED_WITH_MATHEUS, FOUR_DAYS)
    after_first = neglected_life.needs.level(Need.BOND)

    feel(neglected_life, EventKind.TALKED_WITH_MATHEUS, FOUR_DAYS + 0.02)

    second_gain = neglected_life.needs.level(Need.BOND) - after_first
    assert second_gain < 0.1


def test_while_asleep_she_does_not_get_bored(life: EmotionalLife) -> None:
    life.advance(at(10.0))

    assert life.needs.level(Need.NOVELTY) == 1.0


def test_awake_with_nothing_new_she_gets_bored(life: EmotionalLife) -> None:
    stay_awake(life, 0.0, 20.0)

    assert life.rung(Need.NOVELTY).name == "bored"


def test_while_asleep_she_still_misses_him(life: EmotionalLife) -> None:
    life.advance(at(TWO_DAYS))

    assert life.needs.level(Need.BOND) < 1.0


def test_failures_in_a_row_are_counted(life: EmotionalLife) -> None:
    for attempt in range(3):
        feel(life, EventKind.SEARCH_FOUND_NOTHING, 0.1 * attempt)

    assert life.failure_streak == 3


def test_a_success_ends_the_streak_of_failures(life: EmotionalLife) -> None:
    feel(life, EventKind.SEARCH_FOUND_NOTHING, 0.0)

    feel(life, EventKind.SEARCH_FOUND_SOMETHING, 0.1)

    assert life.failure_streak == 0


def test_the_third_failure_in_a_row_stings_more_than_the_first() -> None:
    first_time = create_life()
    feel(first_time, EventKind.SEARCH_FOUND_NOTHING, 0.0)
    after_two = create_life()
    feel(after_two, EventKind.SEARCH_FOUND_NOTHING, 0.0)
    feel(after_two, EventKind.SEARCH_FOUND_NOTHING, 0.0)
    before_third = after_two.emotions.intensity(Emotion.FRUSTRATION)

    feel(after_two, EventKind.SEARCH_FOUND_NOTHING, 0.0)

    third_sting = after_two.emotions.intensity(Emotion.FRUSTRATION) - before_third
    first_sting = first_time.emotions.intensity(Emotion.FRUSTRATION)
    assert third_sting / (1 - before_third) > first_sting


def test_discoveries_in_a_row_start_a_good_tide(life: EmotionalLife) -> None:
    for discovery in range(3):
        feel(life, EventKind.SEARCH_FOUND_SOMETHING, 0.2 * discovery)
        feel(life, EventKind.DISCOVERY_SAVED, 0.2 * discovery + 0.1)

    assert life.is_in_a_good_tide is True


def test_noticing_the_same_kind_of_thing_again_excites_her_less(life: EmotionalLife) -> None:
    before = life.emotions.intensity(Emotion.SURPRISE)
    feel(life, EventKind.NOTICED_SOMETHING, 0.0)
    first_gain = life.emotions.intensity(Emotion.SURPRISE) - before
    middle = life.emotions.intensity(Emotion.SURPRISE)

    feel(life, EventKind.NOTICED_SOMETHING, 0.0)

    second_gain = life.emotions.intensity(Emotion.SURPRISE) - middle
    assert second_gain / (1 - middle) < first_gain / (1 - before)


def test_making_a_wish_leaves_it_pending(life: EmotionalLife) -> None:
    feel(life, EventKind.WISH_MADE, 0.0)

    assert life.pending_wishes == 1


def test_waiting_for_a_wish_makes_her_impatient(life: EmotionalLife) -> None:
    feel(life, EventKind.WISH_MADE, 0.0)

    stay_awake(life, 0.0, 60.0)

    assert life.rung(Need.AUTONOMY).name == "impatient"


def test_with_no_wish_waiting_she_never_grows_impatient(life: EmotionalLife) -> None:
    stay_awake(life, 0.0, 60.0)

    assert life.needs.level(Need.AUTONOMY) == 1.0


def test_a_long_awaited_wish_brings_more_gratitude_than_a_quick_one() -> None:
    quick = create_life()
    feel(quick, EventKind.WISH_GRANTED, 0.0, waited_hours=1.0)
    long_awaited = create_life()
    feel(long_awaited, EventKind.WISH_GRANTED, 0.0, waited_hours=A_WEEK)

    assert long_awaited.emotions.intensity(Emotion.GRATITUDE) > quick.emotions.intensity(
        Emotion.GRATITUDE
    )


def test_a_granted_wish_brings_back_her_hope(life: EmotionalLife) -> None:
    feel(life, EventKind.WISH_MADE, 0.0)
    stay_awake(life, 0.0, 100.0)

    feel(life, EventKind.WISH_GRANTED, 100.0, waited_hours=100.0)

    assert life.rung(Need.AUTONOMY).name == "hopeful"


def test_a_comfort_place_soothes_frustration(life: EmotionalLife) -> None:
    feel(life, EventKind.SEARCH_FOUND_NOTHING, 0.0)
    frustrated = life.emotions.intensity(Emotion.FRUSTRATION)

    feel(life, EventKind.VISITED_COMFORT_PLACE, 0.0)

    assert life.emotions.intensity(Emotion.FRUSTRATION) < frustrated


def test_a_comfort_place_does_not_cure_missing_him(neglected_life: EmotionalLife) -> None:
    rung_before = neglected_life.rung_index(Need.BOND)

    feel(neglected_life, EventKind.VISITED_COMFORT_PLACE, FOUR_DAYS)

    assert neglected_life.rung_index(Need.BOND) == rung_before


def test_a_long_sad_phase_lowers_her_baseline(neglected_life: EmotionalLife) -> None:
    stay_awake(neglected_life, FOUR_DAYS, A_WEEK)

    assert neglected_life.baseline.shift < 0.0


def test_a_less_patient_capybara_grows_impatient_sooner() -> None:
    impatient = EmotionalLife(
        EmotionalLife.newborn(BORN_AT),
        temperament=Temperament(patience=0.0),
        rng=random.Random(7),
        impulse_noise=0.0,
    )
    patient = EmotionalLife(
        EmotionalLife.newborn(BORN_AT),
        temperament=Temperament(patience=1.0),
        rng=random.Random(7),
        impulse_noise=0.0,
    )
    for each_life in (impatient, patient):
        feel(each_life, EventKind.WISH_MADE, 0.0)
        stay_awake(each_life, 0.0, 40.0)

    assert impatient.needs.level(Need.AUTONOMY) < patient.needs.level(Need.AUTONOMY)


def test_going_back_in_time_changes_nothing(life: EmotionalLife) -> None:
    before = life.snapshot()

    life.advance(at(-5.0))

    assert life.snapshot() == before


def test_a_snapshot_brings_her_back_exactly_as_she_was(neglected_life: EmotionalLife) -> None:
    restored = EmotionalLife(neglected_life.snapshot())

    assert restored.snapshot() == neglected_life.snapshot()


def test_never_talked_means_no_hours_since_talking(life: EmotionalLife) -> None:
    assert life.hours_since_talked(at(5.0)) is None


def test_the_bond_ladder_has_a_hurt_rung() -> None:
    assert BOND_LADDER.rungs[HURT_RUNG].name == "hurt"


def test_a_reply_to_her_letter_makes_her_glad(life: EmotionalLife) -> None:
    before = life.emotions.intensity(Emotion.JOY)

    feel(life, EventKind.LETTER_ANSWERED, hours=1.0)

    assert life.emotions.intensity(Emotion.JOY) > before


def test_a_reply_to_her_letter_eases_her_loneliness(life: EmotionalLife) -> None:
    stay_awake(life, 0.0, TWO_DAYS)
    lonely = life.emotions.intensity(Emotion.LONELINESS)

    feel(life, EventKind.LETTER_ANSWERED, hours=TWO_DAYS)

    assert life.emotions.intensity(Emotion.LONELINESS) < lonely
