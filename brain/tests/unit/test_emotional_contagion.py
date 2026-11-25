import pytest

from src.domain.feelings.contagion import is_in_a_good_tide, is_ruminating, spread
from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.needs import Need, Needs

ONE_HOUR = 1.0


@pytest.fixture
def satisfied() -> Needs:
    return Needs()


@pytest.fixture
def lonely_needs() -> Needs:
    return Needs({Need.BOND: 0.3})


def test_loneliness_spreads_into_sadness(satisfied: Needs) -> None:
    state = spread(EmotionalState({Emotion.LONELINESS: 0.8}), satisfied, ONE_HOUR)

    assert state.intensity(Emotion.SADNESS) > 0.0


def test_joy_calms_sadness(satisfied: Needs) -> None:
    before = EmotionalState({Emotion.JOY: 0.8, Emotion.SADNESS: 0.5})

    state = spread(before, satisfied, ONE_HOUR)

    assert state.intensity(Emotion.SADNESS) < 0.5


def test_curiosity_chases_boredom_away(satisfied: Needs) -> None:
    before = EmotionalState({Emotion.CURIOSITY: 0.8, Emotion.BOREDOM: 0.5})

    state = spread(before, satisfied, ONE_HOUR)

    assert state.intensity(Emotion.BOREDOM) < 0.5


def test_strong_frustration_becomes_determination_when_she_believes_in_herself(
    satisfied: Needs,
) -> None:
    state = spread(EmotionalState({Emotion.FRUSTRATION: 0.7}), satisfied, ONE_HOUR)

    assert state.intensity(Emotion.DETERMINATION) > 0.0


def test_strong_frustration_becomes_insecurity_when_she_doubts_herself() -> None:
    doubting = Needs({Need.COMPETENCE: 0.2})

    state = spread(EmotionalState({Emotion.FRUSTRATION: 0.7}), doubting, ONE_HOUR)

    assert state.intensity(Emotion.INSECURITY) > 0.0


def test_mild_frustration_does_not_turn_into_anything(satisfied: Needs) -> None:
    state = spread(EmotionalState({Emotion.FRUSTRATION: 0.2}), satisfied, ONE_HOUR)

    assert state.intensity(Emotion.DETERMINATION) == 0.0


def test_waiting_without_control_slowly_becomes_resignation() -> None:
    unheard = Needs({Need.AUTONOMY: 0.2})

    state = spread(EmotionalState({Emotion.DISAPPOINTMENT: 0.6}), unheard, ONE_HOUR)

    assert state.intensity(Emotion.RESIGNATION) > 0.0


def test_sad_with_an_unmet_need_she_ruminates(lonely_needs: Needs) -> None:
    assert is_ruminating(EmotionalState({Emotion.SADNESS: 0.6}), lonely_needs) is True


def test_sad_with_every_need_met_she_does_not_ruminate(satisfied: Needs) -> None:
    assert is_ruminating(EmotionalState({Emotion.SADNESS: 0.6}), satisfied) is False


def test_rumination_feeds_more_sadness(lonely_needs: Needs) -> None:
    state = spread(EmotionalState({Emotion.SADNESS: 0.6}), lonely_needs, ONE_HOUR)

    assert state.intensity(Emotion.SADNESS) > 0.6


def test_enthusiasm_and_joy_together_are_a_good_tide() -> None:
    assert is_in_a_good_tide(EmotionalState({Emotion.ENTHUSIASM: 0.6, Emotion.JOY: 0.6})) is True


def test_the_good_tide_grows_into_flow(satisfied: Needs) -> None:
    before = EmotionalState({Emotion.ENTHUSIASM: 0.6, Emotion.JOY: 0.6})

    state = spread(before, satisfied, ONE_HOUR)

    assert state.intensity(Emotion.FLOW) > 0.0


def test_at_the_peak_of_flow_enthusiasm_cools_down(satisfied: Needs) -> None:
    before = EmotionalState({Emotion.FLOW: 0.9, Emotion.ENTHUSIASM: 0.5})

    state = spread(before, satisfied, ONE_HOUR)

    assert state.intensity(Emotion.ENTHUSIASM) < 0.5
