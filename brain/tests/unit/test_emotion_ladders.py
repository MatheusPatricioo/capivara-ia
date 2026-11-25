import pytest

from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.ladders import (
    BOND_LADDER,
    CAPYBARA_LADDERS,
    HYSTERESIS_MARGIN,
    RUNG_PULL_HALF_LIFE_HOURS,
    EmotionLadder,
    LadderPosition,
    Rung,
    felt_on,
    moved,
)
from src.domain.feelings.needs import Need

LONELY = 2
SAD = 3
HURT = 4
LONELY_LINE = BOND_LADDER.rungs[LONELY].enters_below
SAD_LINE = BOND_LADDER.rungs[SAD].enters_below


def no_jitter() -> float:
    return 0.0


def move(position: LadderPosition, level: float) -> LadderPosition:
    return moved(BOND_LADDER, position, level, no_jitter)


@pytest.fixture
def lonely() -> LadderPosition:
    return LadderPosition(rung_index=LONELY)


def test_with_a_full_need_she_stays_on_the_first_rung() -> None:
    assert move(LadderPosition(), 1.0).rung_index == 0


def test_she_goes_down_a_rung_when_the_need_crosses_its_line(lonely: LadderPosition) -> None:
    assert move(lonely, SAD_LINE - 0.01).rung_index == SAD


def test_a_sudden_drop_goes_down_several_rungs_at_once() -> None:
    assert move(LadderPosition(), 0.45).rung_index == HURT


def test_just_above_the_line_she_does_not_climb_back_yet() -> None:
    sad = LadderPosition(rung_index=SAD)

    assert move(sad, SAD_LINE + HYSTERESIS_MARGIN / 2).rung_index == SAD


def test_well_above_the_line_she_climbs_back_a_rung() -> None:
    sad = LadderPosition(rung_index=SAD)

    assert move(sad, SAD_LINE + HYSTERESIS_MARGIN).rung_index == LONELY


def test_a_jittered_line_makes_her_fall_a_little_earlier(lonely: LadderPosition) -> None:
    jittered = LadderPosition(rung_index=LONELY, jitter=0.02)

    assert move(jittered, SAD_LINE + 0.01).rung_index == SAD


def test_every_move_rolls_a_new_jitter(lonely: LadderPosition) -> None:
    position = moved(BOND_LADDER, lonely, SAD_LINE - 0.01, lambda: 0.025)

    assert position.jitter == 0.025


def test_a_rung_lifts_the_emotions_it_keeps_alive() -> None:
    sad_rung = BOND_LADDER.rungs[SAD]

    state = felt_on(sad_rung, EmotionalState(), elapsed_hours=RUNG_PULL_HALF_LIFE_HOURS)

    assert state.intensity(Emotion.SADNESS) == pytest.approx(0.45 / 2)


def test_a_rung_holds_down_the_emotions_it_suppresses() -> None:
    apathetic = BOND_LADDER.rungs[-1]

    state = felt_on(apathetic, EmotionalState({Emotion.CURIOSITY: 0.9}), elapsed_hours=5.0)

    assert state.intensity(Emotion.CURIOSITY) < 0.3


def test_every_need_has_a_ladder() -> None:
    assert set(CAPYBARA_LADDERS) == set(Need)


def test_rejects_a_ladder_with_lines_going_up() -> None:
    with pytest.raises(ValueError, match="go down"):
        EmotionLadder(Need.BOND, (Rung("fine", 1.01), Rung("a", 0.5), Rung("b", 0.7)))


def test_rejects_a_ladder_with_a_single_rung() -> None:
    with pytest.raises(ValueError, match="two rungs"):
        EmotionLadder(Need.BOND, (Rung("fine", 1.01),))


def test_her_first_lonely_rung_comes_before_sadness() -> None:
    assert LONELY_LINE > SAD_LINE
