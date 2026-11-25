import random

import pytest

from src.domain.body import Place
from src.domain.feelings.behavior import (
    MAX_CYCLE_PACE,
    Tendency,
    comfort_place,
    cycle_pace,
    tendencies,
)
from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.needs import Need
from tests.fakes.emotional_lives import AlwaysRandom, a_life


@pytest.fixture
def never_surprising() -> random.Random:
    """Every chance roll is high: no surprise place, but a downcast capybara still goes."""
    return AlwaysRandom(0.3)


def test_in_a_good_tide_she_wants_to_explore_boldly() -> None:
    assert tendencies(EmotionalState({Emotion.FLOW: 0.6})) == (Tendency.EXPLORE_BOLDLY,)


def test_bored_she_wants_to_change_subject() -> None:
    assert tendencies(EmotionalState({Emotion.BOREDOM: 0.5})) == (Tendency.CHANGE_SUBJECT,)


def test_resigned_she_stops_asking_for_things() -> None:
    assert tendencies(EmotionalState({Emotion.RESIGNATION: 0.6})) == (Tendency.STOP_ASKING,)


def test_faint_feelings_bring_no_tendency() -> None:
    assert tendencies(EmotionalState({Emotion.BOREDOM: 0.2})) == ()


def test_feeling_her_usual_self_keeps_the_usual_pace() -> None:
    assert cycle_pace(EmotionalState({Emotion.CURIOSITY: 0.45})) == 1.0


def test_apathy_slows_her_down() -> None:
    assert cycle_pace(EmotionalState({Emotion.APATHY: 0.7})) > 1.5


def test_flow_speeds_her_up() -> None:
    assert cycle_pace(EmotionalState({Emotion.FLOW: 0.8})) < 1.0


def test_the_pace_never_slows_beyond_the_limit() -> None:
    state = EmotionalState({Emotion.APATHY: 1.0, Emotion.SADNESS: 1.0})

    assert cycle_pace(state) == MAX_CYCLE_PACE


def test_feeling_fine_she_needs_no_comfort_place(never_surprising: random.Random) -> None:
    life = a_life({Emotion.JOY: 0.5, Emotion.CURIOSITY: 0.5})

    assert comfort_place(life, never_surprising) is None


def test_sad_and_lonely_she_looks_for_the_dog_house(never_surprising: random.Random) -> None:
    life = a_life({Emotion.SADNESS: 0.6, Emotion.LONELINESS: 0.6})

    assert comfort_place(life, never_surprising) is Place.DOG_HOUSE


def test_bored_and_irritated_she_looks_for_the_pond(never_surprising: random.Random) -> None:
    life = a_life({Emotion.BOREDOM: 0.6, Emotion.IRRITATION: 0.6})

    assert comfort_place(life, never_surprising) is Place.POND


def test_simply_worn_out_she_looks_for_the_food_bowl(never_surprising: random.Random) -> None:
    life = a_life({Emotion.JOY: 0.4}, needs={Need.COMFORT: 0.3})

    assert comfort_place(life, never_surprising) is Place.FOOD_BOWL


def test_downcast_she_sometimes_does_not_go_anywhere() -> None:
    life = a_life({Emotion.SADNESS: 0.6, Emotion.LONELINESS: 0.6})

    assert comfort_place(life, AlwaysRandom(0.9)) is None


def test_now_and_then_she_picks_an_unexpected_place() -> None:
    life = a_life({Emotion.SADNESS: 0.6, Emotion.LONELINESS: 0.6})
    surprising = AlwaysRandom(0.1)

    assert comfort_place(life, surprising) in (Place.POND, Place.FOOD_BOWL, Place.DOG_HOUSE)
