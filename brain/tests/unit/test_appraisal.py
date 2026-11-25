import pytest

from src.domain.feelings.appraisal import (
    FAMILIARITY_HALF_LIFE_HOURS,
    EventKind,
    Familiarity,
    scaled_impulses,
)
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.mood import Mood
from src.domain.feelings.temperament import Temperament

FRUSTRATING = {Emotion.FRUSTRATION: 0.4}
JOYFUL = {Emotion.JOY: 0.4}
SOOTHING = {Emotion.SADNESS: -0.4}
NOTICED = EventKind.NOTICED_SOMETHING


def no_noise() -> float:
    return 1.0


@pytest.fixture
def neutral_mood() -> Mood:
    return Mood(valence=0.0)


def test_something_new_lands_at_full_strength() -> None:
    assert Familiarity().habituation(NOTICED) == 1.0


def test_a_repeated_event_lands_softer() -> None:
    assert Familiarity().after(NOTICED).habituation(NOTICED) < 1.0


def test_familiarity_fades_with_time() -> None:
    used_to_it = Familiarity().after(NOTICED)

    faded = used_to_it.faded(FAMILIARITY_HALF_LIFE_HOURS * 10)

    assert faded.habituation(NOTICED) == pytest.approx(1.0, abs=0.01)


def test_a_sensitive_capybara_feels_frustration_harder(neutral_mood: Mood) -> None:
    sensitive = scaled_impulses(
        FRUSTRATING, Temperament(sensitivity=0.9), neutral_mood, 1.0, no_noise
    )
    thick_skinned = scaled_impulses(
        FRUSTRATING, Temperament(sensitivity=0.1), neutral_mood, 1.0, no_noise
    )

    assert sensitive[Emotion.FRUSTRATION] > thick_skinned[Emotion.FRUSTRATION]


def test_a_good_mood_softens_frustration() -> None:
    good = scaled_impulses(FRUSTRATING, Temperament(), Mood(valence=0.6), 1.0, no_noise)
    bad = scaled_impulses(FRUSTRATING, Temperament(), Mood(valence=-0.6), 1.0, no_noise)

    assert good[Emotion.FRUSTRATION] < bad[Emotion.FRUSTRATION]


def test_a_cheerful_capybara_enjoys_good_things_more(neutral_mood: Mood) -> None:
    cheerful = scaled_impulses(JOYFUL, Temperament(cheerfulness=1.0), neutral_mood, 1.0, no_noise)
    gloomy = scaled_impulses(JOYFUL, Temperament(cheerfulness=0.0), neutral_mood, 1.0, no_noise)

    assert cheerful[Emotion.JOY] > gloomy[Emotion.JOY]


def test_soothing_is_not_scaled_by_temperament(neutral_mood: Mood) -> None:
    landed = scaled_impulses(SOOTHING, Temperament(sensitivity=1.0), neutral_mood, 1.0, no_noise)

    assert landed[Emotion.SADNESS] == pytest.approx(-0.4)


def test_a_weaker_strength_makes_every_impulse_smaller(neutral_mood: Mood) -> None:
    landed = scaled_impulses(SOOTHING, Temperament(), neutral_mood, 0.5, no_noise)

    assert landed[Emotion.SADNESS] == pytest.approx(-0.2)


def test_noise_changes_how_hard_an_impulse_lands(neutral_mood: Mood) -> None:
    landed = scaled_impulses(SOOTHING, Temperament(), neutral_mood, 1.0, lambda: 1.1)

    assert landed[Emotion.SADNESS] == pytest.approx(-0.44)
