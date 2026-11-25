import pytest

from src.domain.feelings.emotion import (
    CALM_AROUSAL,
    EMOTION_PROFILES,
    Emotion,
    EmotionalState,
)

JOY_HALF_LIFE = EMOTION_PROFILES[Emotion.JOY].half_life_hours


@pytest.fixture
def happy_state() -> EmotionalState:
    return EmotionalState({Emotion.JOY: 0.8, Emotion.CURIOSITY: 0.5})


@pytest.fixture
def sad_state() -> EmotionalState:
    return EmotionalState({Emotion.SADNESS: 0.8, Emotion.LONELINESS: 0.6})


def test_an_emotion_she_does_not_feel_has_intensity_zero() -> None:
    assert EmotionalState().intensity(Emotion.SADNESS) == 0.0


def test_rejects_an_intensity_above_one() -> None:
    with pytest.raises(ValueError, match="joy"):
        EmotionalState({Emotion.JOY: 1.2})


def test_a_positive_impulse_strengthens_an_emotion() -> None:
    state = EmotionalState().nudged({Emotion.JOY: 0.5})

    assert state.intensity(Emotion.JOY) == pytest.approx(0.5)


def test_an_impulse_on_a_strong_emotion_grows_less(happy_state: EmotionalState) -> None:
    state = happy_state.nudged({Emotion.JOY: 0.5})

    assert state.intensity(Emotion.JOY) == pytest.approx(0.9)


def test_a_negative_impulse_soothes_an_emotion(sad_state: EmotionalState) -> None:
    state = sad_state.nudged({Emotion.SADNESS: -0.5})

    assert state.intensity(Emotion.SADNESS) == pytest.approx(0.4)


def test_nudging_returns_a_new_state(happy_state: EmotionalState) -> None:
    happy_state.nudged({Emotion.JOY: -1.0})

    assert happy_state.intensity(Emotion.JOY) == 0.8


def test_after_one_half_life_an_emotion_fades_halfway_to_rest(
    happy_state: EmotionalState,
) -> None:
    state = happy_state.decayed_towards({Emotion.JOY: 0.2}, elapsed_hours=JOY_HALF_LIFE)

    assert state.intensity(Emotion.JOY) == pytest.approx(0.5)


def test_an_emotion_without_resting_level_fades_towards_zero(
    happy_state: EmotionalState,
) -> None:
    state = happy_state.decayed_towards({}, elapsed_hours=JOY_HALF_LIFE)

    assert state.intensity(Emotion.JOY) == pytest.approx(0.4)


def test_an_emotion_below_its_resting_level_rises_towards_it() -> None:
    state = EmotionalState().decayed_towards({Emotion.JOY: 0.4}, elapsed_hours=JOY_HALF_LIFE)

    assert state.intensity(Emotion.JOY) == pytest.approx(0.2)


def test_a_longer_half_life_makes_an_emotion_linger(happy_state: EmotionalState) -> None:
    state = happy_state.decayed_towards(
        {}, elapsed_hours=JOY_HALF_LIFE, half_life_multipliers={Emotion.JOY: 2.0}
    )

    assert state.intensity(Emotion.JOY) > 0.4


def test_a_floor_lifts_an_emotion_part_of_the_way() -> None:
    state = EmotionalState().pulled_towards({Emotion.SADNESS: 0.6}, share=0.5, raise_only=True)

    assert state.intensity(Emotion.SADNESS) == pytest.approx(0.3)


def test_a_floor_does_not_lower_a_stronger_emotion(sad_state: EmotionalState) -> None:
    state = sad_state.pulled_towards({Emotion.SADNESS: 0.6}, share=0.5, raise_only=True)

    assert state.intensity(Emotion.SADNESS) == 0.8


def test_a_ceiling_lowers_an_emotion_part_of_the_way(happy_state: EmotionalState) -> None:
    state = happy_state.pulled_towards({Emotion.JOY: 0.4}, share=0.5, raise_only=False)

    assert state.intensity(Emotion.JOY) == pytest.approx(0.6)


def test_lists_the_strongest_emotions_first(happy_state: EmotionalState) -> None:
    assert happy_state.strongest(limit=2) == ((Emotion.JOY, 0.8), (Emotion.CURIOSITY, 0.5))


def test_the_strongest_leaves_out_faint_emotions(happy_state: EmotionalState) -> None:
    assert happy_state.strongest(limit=5, minimum=0.6) == ((Emotion.JOY, 0.8),)


def test_good_emotions_give_a_positive_valence(happy_state: EmotionalState) -> None:
    assert happy_state.valence > 0.3


def test_bad_emotions_give_a_negative_valence(sad_state: EmotionalState) -> None:
    assert sad_state.valence < -0.3


def test_feeling_nothing_is_calm() -> None:
    assert EmotionalState().arousal == CALM_AROUSAL


def test_frustration_is_more_agitated_than_sadness() -> None:
    frustrated = EmotionalState({Emotion.FRUSTRATION: 0.7})
    sad = EmotionalState({Emotion.SADNESS: 0.7})

    assert frustrated.arousal > sad.arousal
