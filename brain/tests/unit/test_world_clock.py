from datetime import datetime, time

import pytest

from src.domain.world_clock import ClockMode, DayPhase, WorldClock, WorldTime

ONE_HOUR = 3600.0
HALF_AN_HOUR = 1800.0


def clock_at(
    real_moment: datetime, mode: ClockMode, fast_day_seconds: float = ONE_HOUR
) -> WorldClock:
    return WorldClock(mode, fast_day_seconds, now=lambda: real_moment)


@pytest.fixture
def quarter_past_ten() -> datetime:
    return datetime(2026, 11, 25, 10, 15)


def test_real_mode_follows_the_wall_clock(quarter_past_ten: datetime) -> None:
    clock = clock_at(quarter_past_ten, ClockMode.REAL)

    assert clock.now().time_of_day == time(10, 15)


def test_fast_mode_turns_a_quarter_of_the_real_hour_into_sunrise(
    quarter_past_ten: datetime,
) -> None:
    clock = clock_at(quarter_past_ten, ClockMode.FAST)

    assert clock.now().time_of_day == time(6, 0)


def test_fast_mode_reaches_nightfall_at_minute_forty_five() -> None:
    clock = clock_at(datetime(2026, 11, 25, 10, 45), ClockMode.FAST)

    assert clock.now().phase is DayPhase.NIGHT


def test_a_shorter_fast_day_runs_faster(quarter_past_ten: datetime) -> None:
    clock = clock_at(quarter_past_ten, ClockMode.FAST, fast_day_seconds=HALF_AN_HOUR)

    assert clock.now().time_of_day == time(12, 0)


def test_rejects_a_fast_day_of_zero_seconds(quarter_past_ten: datetime) -> None:
    with pytest.raises(ValueError):
        clock_at(quarter_past_ten, ClockMode.FAST, fast_day_seconds=0)


def test_the_morning_is_day() -> None:
    assert WorldTime(time(10, 0)).phase is DayPhase.DAY


def test_the_sun_rises_at_six() -> None:
    assert WorldTime(time(6, 0)).phase is DayPhase.DAY


def test_night_falls_at_six_in_the_evening() -> None:
    assert WorldTime(time(18, 0)).phase is DayPhase.NIGHT


def test_the_early_morning_is_still_night() -> None:
    assert WorldTime(time(5, 59)).phase is DayPhase.NIGHT


def test_noon_is_half_of_the_day() -> None:
    assert WorldTime(time(12, 0)).day_fraction == pytest.approx(0.5)


def test_a_real_day_lasts_a_whole_day(quarter_past_ten: datetime) -> None:
    assert clock_at(quarter_past_ten, ClockMode.REAL).day_length_seconds == 24 * ONE_HOUR


def test_a_fast_day_lasts_the_configured_time(quarter_past_ten: datetime) -> None:
    assert clock_at(quarter_past_ten, ClockMode.FAST).day_length_seconds == ONE_HOUR


def test_fast_mode_keeps_the_real_date_for_the_moon(quarter_past_ten: datetime) -> None:
    clock = clock_at(quarter_past_ten, ClockMode.FAST)

    assert clock.real_moment() == quarter_past_ten
