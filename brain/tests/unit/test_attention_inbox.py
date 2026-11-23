import threading

import pytest

from src.application.attention_inbox import AttentionInbox
from src.domain.attention import Attention, PointOfAttention

REST_SECONDS = 60.0
THREAD_COUNT = 8
NOTICES_PER_THREAD = 200


class FakeClock:
    """A clock the test moves by hand."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def inbox(clock: FakeClock) -> AttentionInbox:
    return AttentionInbox(Attention(capacity=5, rest_seconds=REST_SECONDS), clock=clock)


def test_noticed_things_wait_in_the_inbox(inbox: AttentionInbox) -> None:
    inbox.notice("water_lilies", "vitórias-régias")

    assert inbox.pending() == (PointOfAttention("water_lilies", "vitórias-régias"),)


def test_uses_the_clock_to_let_things_rest(inbox: AttentionInbox, clock: FakeClock) -> None:
    inbox.notice("water_lilies", "vitórias-régias")
    inbox.let_go("water_lilies")
    clock.now = REST_SECONDS

    assert inbox.notice("water_lilies", "vitórias-régias") is True


def test_many_threads_can_notice_at_the_same_time() -> None:
    inbox = AttentionInbox(Attention(capacity=1000, rest_seconds=REST_SECONDS))

    def notice_many(thread_index: int) -> None:
        for notice_index in range(NOTICES_PER_THREAD):
            inbox.notice(f"thing_{thread_index}_{notice_index}", "algo")

    threads = [threading.Thread(target=notice_many, args=(index,)) for index in range(THREAD_COUNT)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(inbox.pending()) == 1000
