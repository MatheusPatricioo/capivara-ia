import pytest

from src.domain.feelings.baseline import BASELINE_HALF_LIFE_HOURS, MAX_SHIFT, Baseline
from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.mood import MOOD_HALF_LIFE_HOURS, Mood

NATURAL_MOOD = 0.4


@pytest.fixture
def sad_state() -> EmotionalState:
    return EmotionalState({Emotion.SADNESS: 0.9, Emotion.LONELINESS: 0.8})


def test_mood_moves_halfway_to_her_feelings_in_one_half_life(sad_state: EmotionalState) -> None:
    mood = Mood(valence=0.4).followed(sad_state, elapsed_hours=MOOD_HALF_LIFE_HOURS)

    assert mood.valence == pytest.approx((0.4 + sad_state.valence) / 2)


def test_one_bad_moment_barely_changes_the_mood(sad_state: EmotionalState) -> None:
    mood = Mood(valence=0.4).followed(sad_state, elapsed_hours=0.1)

    assert mood.valence > 0.35


def test_a_good_day_spirit_lifts_the_mood() -> None:
    plain = Mood().followed(EmotionalState(), elapsed_hours=1.0)
    lucky = Mood().followed(EmotionalState(), elapsed_hours=1.0, day_spirit=0.1)

    assert lucky.valence > plain.valence


def test_in_a_good_mood_bad_things_hit_softer() -> None:
    assert Mood(valence=0.5).negative_impact < 1.0


def test_in_a_bad_mood_bad_things_hit_harder() -> None:
    assert Mood(valence=-0.5).negative_impact > 1.0


def test_in_a_bad_mood_good_things_are_enjoyed_less() -> None:
    assert Mood(valence=-0.5).positive_impact < 1.0


def test_rejects_a_mood_valence_outside_the_range() -> None:
    with pytest.raises(ValueError, match="valence"):
        Mood(valence=1.5)


def test_a_long_bad_mood_pushes_the_baseline_down() -> None:
    baseline = Baseline().drifted(-0.6, NATURAL_MOOD, elapsed_hours=BASELINE_HALF_LIFE_HOURS)

    assert baseline.shift == pytest.approx(-0.25)


def test_the_baseline_never_moves_beyond_its_limit() -> None:
    baseline = Baseline().drifted(-1.0, NATURAL_MOOD, elapsed_hours=BASELINE_HALF_LIFE_HOURS * 20)

    assert baseline.shift == pytest.approx(-MAX_SHIFT)


def test_one_bad_hour_barely_moves_the_baseline() -> None:
    baseline = Baseline().drifted(-0.4, NATURAL_MOOD, elapsed_hours=1.0)

    assert baseline.shift > -0.01


def test_her_natural_mood_brings_the_baseline_back_home() -> None:
    baseline = Baseline(-0.4).drifted(
        NATURAL_MOOD, NATURAL_MOOD, elapsed_hours=BASELINE_HALF_LIFE_HOURS
    )

    assert baseline.shift == pytest.approx(-0.2)


def test_rejects_a_shift_beyond_the_limit() -> None:
    with pytest.raises(ValueError, match="shift"):
        Baseline(0.8)
