"""Her feelings flowing through the real pieces: tools, the JSON file and two processes."""

import random
from pathlib import Path

import pytest

from src.application.attention_inbox import AttentionInbox
from src.application.heart import Heart
from src.application.tools.feeling_tool import FeelingTool, search_feeling
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.attention import Attention
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.needs import Need
from src.domain.web_search import SearchResult
from src.infrastructure.json_emotional_memory import JsonEmotionalMemory
from src.infrastructure.world_messages import NoticedMessage
from src.live_capybara import attention_listener

NOW = 1_800_000_000.0
FOUR_DAYS = 4 * 86400.0
TALKED = EmotionalEvent(EventKind.TALKED_WITH_MATHEUS)
SAD_RUNG = 3


class FakeClock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> float:
        return self.now


class EmptyWebSearcher:
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        return []


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def feelings_file(tmp_path: Path) -> Path:
    return tmp_path / "feelings.json"


def open_heart(feelings_file: Path, clock: FakeClock) -> Heart:
    """Each call is like another process opening the same feelings file."""
    return Heart(JsonEmotionalMemory(feelings_file), rng=random.Random(5), clock=clock)


def test_searches_that_find_nothing_frustrate_her_more_and_more(
    feelings_file: Path, clock: FakeClock
) -> None:
    heart = open_heart(feelings_file, clock)
    search = FeelingTool(WebSearchTool(EmptyWebSearcher()), heart, search_feeling)

    for query in ("buracos negros", "quasares", "pulsares"):
        search.run({"query": query})

    assert heart.check_in().failure_streak == 3


def test_what_the_chat_felt_reaches_the_live_capybara(
    feelings_file: Path, clock: FakeClock
) -> None:
    open_heart(feelings_file, clock).feel(TALKED)
    clock.now += FOUR_DAYS
    open_heart(feelings_file, clock).feel(TALKED)

    live = open_heart(feelings_file, clock).check_in()

    assert live.emotions.intensity(Emotion.HURT) > 0.0


def test_four_days_alone_she_misses_him_even_after_a_restart(
    feelings_file: Path, clock: FakeClock
) -> None:
    open_heart(feelings_file, clock).feel(TALKED)
    clock.now += FOUR_DAYS

    after_restart = open_heart(feelings_file, clock).check_in()

    assert after_restart.rung_index(Need.BOND) >= SAD_RUNG


def test_something_new_in_the_world_makes_her_curious(
    feelings_file: Path, clock: FakeClock
) -> None:
    heart = open_heart(feelings_file, clock)
    before = heart.check_in().emotions.intensity(Emotion.SURPRISE)
    notice = attention_listener(AttentionInbox(Attention(5, 60.0)), heart)

    notice(NoticedMessage(thing="big_oak", description="um carvalho enorme"))

    assert heart.check_in().emotions.intensity(Emotion.SURPRISE) > before
