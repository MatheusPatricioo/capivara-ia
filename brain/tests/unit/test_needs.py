import pytest

from src.domain.feelings.needs import Need, NeedRhythm, Needs

BOND_HOURS_TO_EMPTY = 100.0


@pytest.fixture
def rhythm() -> NeedRhythm:
    return NeedRhythm(
        {
            Need.BOND: BOND_HOURS_TO_EMPTY,
            Need.NOVELTY: 10.0,
            Need.COMPETENCE: 50.0,
            Need.AUTONOMY: 200.0,
            Need.COMFORT: 20.0,
        }
    )


def test_a_need_she_never_felt_starts_full() -> None:
    assert Needs().level(Need.BOND) == 1.0


def test_needs_empty_with_time(rhythm: NeedRhythm) -> None:
    needs = Needs().depleted(rhythm, elapsed_hours=25.0)

    assert needs.level(Need.BOND) == pytest.approx(0.75)


def test_a_need_never_goes_below_empty(rhythm: NeedRhythm) -> None:
    needs = Needs().depleted(rhythm, elapsed_hours=1000.0)

    assert needs.level(Need.BOND) == 0.0


def test_a_multiplier_of_zero_freezes_a_need(rhythm: NeedRhythm) -> None:
    needs = Needs().depleted(rhythm, elapsed_hours=25.0, multipliers={Need.BOND: 0.0})

    assert needs.level(Need.BOND) == 1.0


def test_a_faster_time_scale_empties_needs_sooner() -> None:
    fast = NeedRhythm(time_scale=10.0)

    assert fast.depletion_per_hour(Need.BOND) == pytest.approx(
        NeedRhythm().depletion_per_hour(Need.BOND) * 10
    )


def test_refilling_a_need_never_goes_above_full() -> None:
    needs = Needs({Need.BOND: 0.8}).changed({Need.BOND: 0.5})

    assert needs.level(Need.BOND) == 1.0


def test_the_most_unmet_need_is_the_emptiest() -> None:
    needs = Needs({Need.BOND: 0.3, Need.NOVELTY: 0.6})

    assert needs.most_unmet() is Need.BOND


def test_rejects_a_rhythm_without_every_need() -> None:
    with pytest.raises(ValueError, match="hours to empty"):
        NeedRhythm({Need.BOND: 10.0})


def test_rejects_a_level_above_full() -> None:
    with pytest.raises(ValueError, match="bond"):
        Needs({Need.BOND: 1.5})
