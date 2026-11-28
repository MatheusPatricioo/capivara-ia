from datetime import UTC, datetime

import pytest

from src.domain.moon import moon_phase

# Real phases of January 2024, in UTC. The average cycle can be off by a few hours,
# so a tolerance of 0.02 (about 14 hours) is allowed.
TOLERANCE = 0.02


def test_a_day_after_a_new_moon_is_near_the_start_of_the_cycle() -> None:
    assert moon_phase(datetime(2024, 1, 12, 12, 0, tzinfo=UTC)) == pytest.approx(
        0.034, abs=TOLERANCE
    )


def test_the_first_quarter_is_a_quarter_of_the_cycle() -> None:
    assert moon_phase(datetime(2024, 1, 18, 3, 53, tzinfo=UTC)) == pytest.approx(
        0.25, abs=TOLERANCE
    )


def test_the_full_moon_is_half_of_the_cycle() -> None:
    assert moon_phase(datetime(2024, 1, 25, 17, 54, tzinfo=UTC)) == pytest.approx(
        0.5, abs=TOLERANCE
    )


def test_the_last_quarter_is_three_quarters_of_the_cycle() -> None:
    assert moon_phase(datetime(2024, 2, 2, 23, 18, tzinfo=UTC)) == pytest.approx(
        0.75, abs=TOLERANCE
    )


def test_a_date_before_the_known_new_moon_still_falls_inside_the_cycle() -> None:
    assert 0.0 <= moon_phase(datetime(1999, 12, 25, tzinfo=UTC)) < 1.0
