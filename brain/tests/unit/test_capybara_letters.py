from typing import Any, cast

import pytest

from src.capybara_letters import CapybaraLetters


class RecordingWriter:
    def __init__(self, timeline: list[str]) -> None:
        self._timeline = timeline

    def maybe_write(self) -> None:
        self._timeline.append("write a letter")


class RecordingReplyReader:
    def __init__(self, timeline: list[str]) -> None:
        self._timeline = timeline

    def read_new_replies(self) -> None:
        self._timeline.append("read his replies")

    def release(self) -> None:
        self._timeline.append("remember the replies as read")


@pytest.fixture
def timeline() -> list[str]:
    return []


@pytest.fixture
def letters(timeline: list[str]) -> CapybaraLetters:
    writer: Any = RecordingWriter(timeline)
    reply_reader: Any = RecordingReplyReader(timeline)
    return CapybaraLetters(cast(Any, writer), cast(Any, reply_reader))


def test_before_a_cycle_she_reads_his_replies_before_writing(
    letters: CapybaraLetters, timeline: list[str]
) -> None:
    letters.before_cycle()

    assert timeline == ["read his replies", "write a letter"]


def test_after_a_cycle_the_replies_are_remembered_as_read(
    letters: CapybaraLetters, timeline: list[str]
) -> None:
    letters.after_cycle()

    assert timeline == ["remember the replies as read"]
