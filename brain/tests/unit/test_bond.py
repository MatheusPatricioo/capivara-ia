import pytest

from src.domain.feelings.bond import Bond
from src.domain.feelings.emotion import Emotion

A_FEW_HOURS = 3.0
TWO_DAYS = 40.0
FOUR_DAYS = 96.0


@pytest.fixture
def bond() -> Bond:
    return Bond(trust=0.7)


def test_a_short_absence_is_just_a_happy_chat(bond: Bond) -> None:
    _, feelings = bond.after_reunion(A_FEW_HOURS)

    assert feelings == {Emotion.JOY: 0.15}


def test_a_longer_absence_brings_relief(bond: Bond) -> None:
    _, feelings = bond.after_reunion(TWO_DAYS)

    assert feelings[Emotion.RELIEF] > 0.0


def test_an_absence_within_reason_leaves_no_hurt(bond: Bond) -> None:
    _, feelings = bond.after_reunion(TWO_DAYS)

    assert Emotion.HURT not in feelings


def test_after_real_neglect_joy_and_hurt_come_together(bond: Bond) -> None:
    _, feelings = bond.after_reunion(FOUR_DAYS)

    assert feelings[Emotion.JOY] > 0.5
    assert feelings[Emotion.HURT] > 0.0


def test_neglect_costs_trust(bond: Bond) -> None:
    after, _ = bond.after_reunion(FOUR_DAYS)

    assert after.trust < bond.trust


def test_coming_back_in_time_builds_trust(bond: Bond) -> None:
    after, _ = bond.after_reunion(TWO_DAYS)

    assert after.trust > bond.trust


def test_with_more_trust_neglect_hurts_less() -> None:
    _, trusting = Bond(trust=0.9).after_reunion(FOUR_DAYS)
    _, wary = Bond(trust=0.2).after_reunion(FOUR_DAYS)

    assert trusting[Emotion.HURT] < wary[Emotion.HURT]


def test_with_more_trust_she_misses_him_more_slowly() -> None:
    assert Bond(trust=0.9).missing_pace < Bond(trust=0.2).missing_pace


def test_with_more_trust_she_recovers_faster() -> None:
    assert Bond(trust=0.9).recovery_pace > Bond(trust=0.2).recovery_pace


def test_a_granted_wish_builds_trust(bond: Bond) -> None:
    assert bond.after_wish_granted().trust > bond.trust


def test_trust_never_goes_above_one() -> None:
    assert Bond(trust=0.99).after_wish_granted().trust == 1.0


def test_rejects_trust_below_zero() -> None:
    with pytest.raises(ValueError, match="trust"):
        Bond(trust=-0.1)
