import threading

import pytest

from src.application.creator_presence import CreatorPresence
from tests.fakes.manual_time import ManualTime

QUIET_SECONDS = 120.0


@pytest.fixture
def time() -> ManualTime:
    return ManualTime()


@pytest.fixture
def presence(time: ManualTime) -> CreatorPresence:
    return CreatorPresence(QUIET_SECONDS, clock=time.clock, sleep=time.sleep)


def test_nobody_is_talking_before_the_first_message(presence: CreatorPresence) -> None:
    assert not presence.is_talking()


def test_an_exchange_starts_a_conversation(presence: CreatorPresence) -> None:
    presence.mark_exchange()

    assert presence.is_talking()


def test_the_conversation_ends_after_the_quiet_time(
    presence: CreatorPresence, time: ManualTime
) -> None:
    presence.mark_exchange()
    time.now += QUIET_SECONDS

    assert not presence.is_talking()


def test_ending_stops_the_conversation_before_the_quiet_time(presence: CreatorPresence) -> None:
    presence.mark_exchange()

    presence.end()

    assert not presence.is_talking()


def test_a_reply_after_the_end_does_not_renew_the_conversation(
    presence: CreatorPresence,
) -> None:
    presence.mark_exchange()
    presence.end()

    assert (presence.mark_reply(), presence.is_talking()) == (False, False)


def test_a_reply_during_the_conversation_renews_it(
    presence: CreatorPresence, time: ManualTime
) -> None:
    presence.mark_exchange()
    time.now += 100.0

    presence.mark_reply()
    time.now += 100.0

    assert presence.is_talking()


def test_a_new_message_after_the_end_starts_a_new_conversation(
    presence: CreatorPresence,
) -> None:
    presence.end()

    presence.mark_exchange()

    assert presence.is_talking()


def test_ending_wakes_up_a_loop_that_waits_for_the_quiet_time() -> None:
    presence = CreatorPresence(QUIET_SECONDS)
    presence.mark_exchange()
    waiting_loop = threading.Thread(target=presence.wait_while_talking)
    waiting_loop.start()

    presence.end()
    waiting_loop.join(timeout=2.0)

    assert not waiting_loop.is_alive()


def test_waiting_without_a_conversation_does_not_sleep(
    presence: CreatorPresence, time: ManualTime
) -> None:
    presence.wait_while_talking()

    assert time.sleeps == []


def test_waiting_sleeps_what_is_left_of_the_quiet_time(
    presence: CreatorPresence, time: ManualTime
) -> None:
    presence.mark_exchange()
    time.now += 20.0

    presence.wait_while_talking()

    assert time.sleeps == [100.0]


def test_a_message_during_the_wait_makes_it_wait_the_whole_quiet_time_again(
    presence: CreatorPresence, time: ManualTime
) -> None:
    presence.mark_exchange()
    time.while_sleeping(presence.mark_exchange)

    presence.wait_while_talking()

    assert time.sleeps == [QUIET_SECONDS, QUIET_SECONDS]
