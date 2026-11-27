from src.application.feelings_narrator import (
    CALM,
    GOOD_TIDE,
    RUMINATING,
    STILL_MISSING_HIM,
    describe_feelings,
)
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.needs import Need
from tests.fakes.emotional_lives import NOW, a_life

LONELY_RUNG = 2
BORED_RUNG = 2
RESIGNED_RUNG = 3


def test_feeling_nothing_strong_she_is_calm() -> None:
    assert describe_feelings(a_life({Emotion.JOY: 0.1}), NOW) == f"- {CALM}"


def test_tells_her_strongest_emotions_with_how_strong_they_are() -> None:
    life = a_life({Emotion.CURIOSITY: 0.8, Emotion.JOY: 0.5, Emotion.SURPRISE: 0.3})

    described = describe_feelings(life, NOW)

    assert "Você está muito curiosa, bem feliz e um pouco surpresa." in described


def test_tells_how_long_matheus_has_been_away() -> None:
    life = a_life({Emotion.LONELINESS: 0.5}, rungs={Need.BOND: LONELY_RUNG}, hours_since_talked=50)

    described = describe_feelings(life, NOW)

    assert "Faz 2 dias que o criador não conversa com você, e você se sente sozinha." in described


def test_an_absence_shorter_than_a_day_is_told_in_hours() -> None:
    life = a_life(rungs={Need.BOND: 1}, hours_since_talked=13.2)

    assert "Faz 13 horas" in describe_feelings(life, NOW)


def test_right_after_he_is_back_the_absence_still_weighs() -> None:
    life = a_life(rungs={Need.BOND: LONELY_RUNG}, hours_since_talked=0.2)

    assert STILL_MISSING_HIM in describe_feelings(life, NOW)


def test_a_need_on_its_first_rung_has_no_cause_to_tell() -> None:
    life = a_life({Emotion.JOY: 0.5}, hours_since_talked=2)

    assert "criador" not in describe_feelings(life, NOW)


def test_tells_why_she_is_bored() -> None:
    life = a_life({Emotion.BOREDOM: 0.5}, rungs={Need.NOVELTY: BORED_RUNG})

    assert "faz tempo que não aprende nada novo" in describe_feelings(life, NOW)


def test_tells_when_she_ruminates() -> None:
    life = a_life({Emotion.SADNESS: 0.6}, needs={Need.BOND: 0.3})

    assert RUMINATING in describe_feelings(life, NOW)


def test_tells_when_she_is_in_a_good_tide() -> None:
    life = a_life({Emotion.ENTHUSIASM: 0.6, Emotion.JOY: 0.6})

    assert GOOD_TIDE in describe_feelings(life, NOW)


def test_tells_what_she_feels_like_doing() -> None:
    life = a_life({Emotion.RESIGNATION: 0.6}, rungs={Need.AUTONOMY: RESIGNED_RUNG})

    assert "Você não está com vontade de pedir nada pro criador." in describe_feelings(life, NOW)


def test_every_line_is_a_list_item() -> None:
    life = a_life({Emotion.BOREDOM: 0.5}, rungs={Need.NOVELTY: BORED_RUNG})

    lines = describe_feelings(life, NOW).splitlines()

    assert all(line.startswith("- ") for line in lines)
