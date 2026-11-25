import logging
import random

import pytest

from src.application.heart import Heart
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.feelings.needs import Need
from tests.fakes.in_memory_emotional_memory import BrokenEmotionalMemory, InMemoryEmotionalMemory

NOW = 1_800_000_000.0
ONE_DAY = 86400.0
TALKED = EmotionalEvent(EventKind.TALKED_WITH_MATHEUS)
NOTHING_FOUND = EmotionalEvent(EventKind.SEARCH_FOUND_NOTHING)
HEART_LOGGER = "src.application.heart"


class FakeClock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def memory() -> InMemoryEmotionalMemory:
    return InMemoryEmotionalMemory()


@pytest.fixture
def heart(memory: InMemoryEmotionalMemory, clock: FakeClock) -> Heart:
    return Heart(memory, rng=random.Random(1), clock=clock)


def test_her_first_feeling_starts_her_emotional_life(heart: Heart) -> None:
    life = heart.check_in()

    assert life.emotions.strongest(limit=1)[0][0] in (Emotion.CURIOSITY, Emotion.JOY)


def test_what_she_feels_is_saved(heart: Heart, memory: InMemoryEmotionalMemory) -> None:
    heart.feel(NOTHING_FOUND)

    assert memory.snapshot is not None
    assert memory.snapshot.emotions.intensity(Emotion.FRUSTRATION) > 0.0


def test_time_passes_between_two_moments(heart: Heart, clock: FakeClock) -> None:
    heart.feel(TALKED)
    clock.now += 2 * ONE_DAY

    life = heart.check_in()

    assert life.needs.level(Need.BOND) < 0.8


def test_checking_in_tells_her_how_many_wishes_are_waiting(heart: Heart) -> None:
    assert heart.check_in(pending_wishes=2).pending_wishes == 2


def test_two_hearts_sharing_a_memory_share_one_emotional_life(
    memory: InMemoryEmotionalMemory, clock: FakeClock
) -> None:
    chat_heart = Heart(memory, clock=clock)
    live_heart = Heart(memory, clock=clock)
    chat_heart.feel(TALKED)

    assert live_heart.check_in().hours_since_talked(clock.now) == 0.0


def test_with_a_broken_memory_she_keeps_feeling(clock: FakeClock) -> None:
    heart = Heart(BrokenEmotionalMemory(), clock=clock)
    heart.feel(NOTHING_FOUND)

    life = heart.feel(NOTHING_FOUND)

    assert life.failure_streak == 2


def test_a_broken_memory_is_logged(clock: FakeClock, caplog: pytest.LogCaptureFixture) -> None:
    heart = Heart(BrokenEmotionalMemory(), clock=clock)

    with caplog.at_level(logging.WARNING, logger=HEART_LOGGER):
        heart.feel(NOTHING_FOUND)

    assert "Could not save her emotional life" in caplog.text


def test_every_change_is_shown(memory: InMemoryEmotionalMemory, clock: FakeClock) -> None:
    shown: list[EmotionalLife] = []
    heart = Heart(memory, clock=clock)
    heart.watch(shown.append)

    heart.feel(TALKED)

    assert len(shown) == 1


def test_a_failure_to_show_her_feelings_does_not_stop_her_feeling(
    memory: InMemoryEmotionalMemory, clock: FakeClock
) -> None:
    def broken_display(life: EmotionalLife) -> None:
        raise RuntimeError("the world is gone")

    heart = Heart(memory, clock=clock)
    heart.watch(broken_display)
    heart.feel(TALKED)

    assert memory.saves == 1
