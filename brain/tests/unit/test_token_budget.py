import pytest

from src.application.token_budget import HourlyTokenBudget

MAX_TOKENS_PER_HOUR = 1000


class FakeClock:
    """A clock the test moves by hand, in seconds."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def budget(clock: FakeClock) -> HourlyTokenBudget:
    return HourlyTokenBudget(MAX_TOKENS_PER_HOUR, clock=clock)


def test_starts_with_room(budget: HourlyTokenBudget) -> None:
    assert budget.has_room()


def test_sums_the_tokens_recorded_in_the_last_hour(
    budget: HourlyTokenBudget, clock: FakeClock
) -> None:
    budget.record(300)
    clock.now = 1800.0
    budget.record(200)

    assert budget.tokens_used_in_the_last_hour == 500


def test_has_no_room_when_the_limit_is_reached(budget: HourlyTokenBudget) -> None:
    budget.record(MAX_TOKENS_PER_HOUR)

    assert not budget.has_room()


def test_forgets_tokens_older_than_one_hour(budget: HourlyTokenBudget, clock: FakeClock) -> None:
    budget.record(MAX_TOKENS_PER_HOUR)
    clock.now = 3600.0

    assert budget.has_room()


def test_rejects_a_limit_of_zero() -> None:
    with pytest.raises(ValueError):
        HourlyTokenBudget(0)
