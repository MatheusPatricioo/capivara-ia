import pytest

from src.domain.feelings.baseline import Baseline
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.temperament import Temperament


@pytest.fixture
def capybara() -> Temperament:
    return Temperament()


def test_at_rest_she_is_more_curious_than_anything(capybara: Temperament) -> None:
    resting = capybara.resting_levels(Baseline())

    assert max(resting, key=lambda emotion: resting[emotion]) is Emotion.CURIOSITY


def test_at_rest_with_her_usual_baseline_she_feels_no_sadness(capybara: Temperament) -> None:
    assert capybara.resting_levels(Baseline())[Emotion.SADNESS] == 0.0


def test_a_lowered_baseline_leaves_some_sadness_at_rest(capybara: Temperament) -> None:
    assert capybara.resting_levels(Baseline(-0.5))[Emotion.SADNESS] > 0.0


def test_a_lowered_baseline_means_less_joy_at_rest(capybara: Temperament) -> None:
    usual = capybara.resting_levels(Baseline())[Emotion.JOY]
    lowered = capybara.resting_levels(Baseline(-0.5))[Emotion.JOY]

    assert lowered < usual


def test_a_raised_baseline_means_more_curiosity_at_rest(capybara: Temperament) -> None:
    usual = capybara.resting_levels(Baseline())[Emotion.CURIOSITY]
    raised = capybara.resting_levels(Baseline(0.5))[Emotion.CURIOSITY]

    assert raised > usual


def test_her_natural_mood_is_good(capybara: Temperament) -> None:
    assert capybara.natural_mood() > 0.3


def test_a_sensitive_capybara_is_hit_harder_by_bad_things() -> None:
    assert (
        Temperament(sensitivity=0.9).negative_impact > Temperament(sensitivity=0.1).negative_impact
    )


def test_an_impatient_capybara_wears_down_faster_while_waiting() -> None:
    assert Temperament(patience=0.1).impatience_pace > Temperament(patience=0.9).impatience_pace


def test_resilience_shortens_bad_emotions(capybara: Temperament) -> None:
    assert capybara.half_life_multipliers()[Emotion.SADNESS] < 1.0


def test_resilience_does_not_change_good_emotions(capybara: Temperament) -> None:
    assert Emotion.JOY not in capybara.half_life_multipliers()


def test_rejects_a_trait_above_one() -> None:
    with pytest.raises(ValueError, match="patience"):
        Temperament(patience=1.5)
