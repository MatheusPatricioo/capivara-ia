"""Talking with her creator comes first: a message that arrives during an autonomous cycle
pauses the cycle before its next step, and the cycle goes on after the quiet time."""

from collections.abc import Sequence

import pytest

from src.application.autonomous_loop import AutonomousLoop
from src.application.conversation import Conversation
from src.application.creator_presence import CreatorPresence
from src.application.token_budget import HourlyTokenBudget
from src.domain.language_model import ChatMessage, Role, ToolCall, ToolDefinition
from tests.fakes.manual_time import ManualTime

QUIET_SECONDS = 120.0
INNER_VOICE = "O que você quer fazer agora?"
THOUGHT = "Vou pesquisar sobre vaga-lumes."
SEARCH_CALL = ToolCall(name="web_search", arguments={"query": "vaga-lumes"})


class SearchWhileHerCreatorArrives:
    """A search tool that takes a while: her creator sends a message while it runs."""

    def __init__(self, presence: CreatorPresence) -> None:
        self._presence = presence

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="web_search", description="Searches the web.", parameters={})

    def run(self, arguments: dict[str, object]) -> str:
        self._presence.mark_exchange()
        return "Vaga-lumes brilham para se comunicar."


class TimedLanguageModel:
    """Searches first, then thinks; records the moment of every call."""

    def __init__(self, time: ManualTime) -> None:
        self._time = time
        self._replies = iter(
            [
                ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH_CALL,)),
                ChatMessage(Role.ASSISTANT, THOUGHT),
            ]
        )
        self.called_at: list[float] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.called_at.append(self._time.now)
        return next(self._replies)


@pytest.fixture
def time() -> ManualTime:
    return ManualTime()


@pytest.fixture
def presence(time: ManualTime) -> CreatorPresence:
    return CreatorPresence(QUIET_SECONDS, clock=time.clock, sleep=time.sleep)


@pytest.fixture
def language_model(time: ManualTime) -> TimedLanguageModel:
    return TimedLanguageModel(time)


@pytest.fixture
def loop(language_model: TimedLanguageModel, presence: CreatorPresence) -> AutonomousLoop:
    def start_conversation() -> Conversation:
        return Conversation(
            language_model,
            "Você é uma capivara curiosa.",
            tools=[SearchWhileHerCreatorArrives(presence)],
            before_step=presence.wait_while_talking,
        )

    return AutonomousLoop(
        start_conversation,
        HourlyTokenBudget(max_tokens_per_hour=1000),
        compose_inner_voice=lambda: INNER_VOICE,
        interval_seconds=60.0,
        wait_for_turn=presence.wait_while_talking,
    )


def test_a_message_during_the_cycle_pauses_the_next_step(
    loop: AutonomousLoop, time: ManualTime
) -> None:
    loop.run_cycle()

    assert time.sleeps == [QUIET_SECONDS]


def test_the_cycle_goes_on_after_the_quiet_time(
    loop: AutonomousLoop, language_model: TimedLanguageModel
) -> None:
    thought = loop.run_cycle()

    assert (thought, language_model.called_at) == (THOUGHT, [0.0, QUIET_SECONDS])


def test_a_cycle_waits_to_start_while_they_are_talking(
    loop: AutonomousLoop, presence: CreatorPresence, language_model: TimedLanguageModel
) -> None:
    presence.mark_exchange()

    loop.run_cycle()

    assert language_model.called_at[0] == QUIET_SECONDS
