import logging
from collections.abc import Sequence

import pytest
from opentelemetry.trace import StatusCode

from src.application.autonomous_loop import AutonomousLoop
from src.application.conversation import Conversation
from src.application.token_budget import HourlyTokenBudget
from src.domain.language_model import ChatMessage, LanguageModelError, Role, ToolDefinition
from tests.fakes.recorded_spans import RecordedSpans

INNER_VOICE = "(Você está sozinha. O que quer fazer?)"
THOUGHT = "Acho que vou olhar as nuvens no laguinho."
INTERVAL_SECONDS = 120.0
MAX_TOKENS_PER_HOUR = 1000
AUTONOMOUS_LOOP_LOGGER = "src.application.autonomous_loop"


class ThinkingLanguageModel:
    """Always answers with the same thought and remembers what it received."""

    def __init__(self) -> None:
        self.received_messages: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        self.received_messages.append(messages)
        return ChatMessage(Role.ASSISTANT, THOUGHT)


class OfflineLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        raise LanguageModelError("Ollama is not running")


@pytest.fixture
def language_model() -> ThinkingLanguageModel:
    return ThinkingLanguageModel()


@pytest.fixture
def budget() -> HourlyTokenBudget:
    return HourlyTokenBudget(MAX_TOKENS_PER_HOUR)


@pytest.fixture
def started_conversations() -> list[Conversation]:
    return []


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def thoughts() -> list[str]:
    return []


@pytest.fixture
def loop(
    language_model: ThinkingLanguageModel,
    budget: HourlyTokenBudget,
    started_conversations: list[Conversation],
    sleeps: list[float],
    thoughts: list[str],
) -> AutonomousLoop:
    def start_conversation() -> Conversation:
        conversation = Conversation(language_model, "You are a capybara.")
        started_conversations.append(conversation)
        return conversation

    return AutonomousLoop(
        start_conversation,
        budget,
        lambda: INNER_VOICE,
        INTERVAL_SECONDS,
        on_thought=thoughts.append,
        sleep=sleeps.append,
    )


def test_a_cycle_returns_what_the_capybara_thought(loop: AutonomousLoop) -> None:
    assert loop.run_cycle() == THOUGHT


def test_a_cycle_sends_the_inner_voice_as_the_message(
    loop: AutonomousLoop, language_model: ThinkingLanguageModel
) -> None:
    loop.run_cycle()

    assert language_model.received_messages[0][-1] == ChatMessage(Role.USER, INNER_VOICE)


def test_a_cycle_shares_the_thought(loop: AutonomousLoop, thoughts: list[str]) -> None:
    loop.run_cycle()

    assert thoughts == [THOUGHT]


def test_each_cycle_starts_a_fresh_conversation(
    loop: AutonomousLoop, started_conversations: list[Conversation]
) -> None:
    loop.run(cycles=2)

    assert len(started_conversations) == 2


def test_waits_the_interval_between_cycles_but_not_before_the_first(
    loop: AutonomousLoop, sleeps: list[float]
) -> None:
    loop.run(cycles=3)

    assert sleeps == [INTERVAL_SECONDS, INTERVAL_SECONDS]


def test_skips_the_cycle_when_the_token_budget_is_spent(
    loop: AutonomousLoop, budget: HourlyTokenBudget, language_model: ThinkingLanguageModel
) -> None:
    budget.record(MAX_TOKENS_PER_HOUR)

    assert loop.run_cycle() is None
    assert language_model.received_messages == []


def test_a_failed_cycle_returns_none_and_logs_a_warning(
    budget: HourlyTokenBudget, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=AUTONOMOUS_LOOP_LOGGER)
    loop = AutonomousLoop(
        lambda: Conversation(OfflineLanguageModel(), "You are a capybara."),
        budget,
        lambda: INNER_VOICE,
        INTERVAL_SECONDS,
    )

    assert loop.run_cycle() is None
    assert caplog.messages == ["Cycle failed: Ollama is not running"]


def test_composes_the_inner_voice_again_for_every_cycle(
    budget: HourlyTokenBudget, language_model: ThinkingLanguageModel
) -> None:
    inner_voices = iter(["(primeiro ciclo)", "(segundo ciclo)"])
    loop = AutonomousLoop(
        lambda: Conversation(language_model, "You are a capybara."),
        budget,
        lambda: next(inner_voices),
        INTERVAL_SECONDS,
        sleep=lambda seconds: None,
    )

    loop.run(cycles=2)

    sent_messages = [messages[-1].content for messages in language_model.received_messages]
    assert sent_messages == ["(primeiro ciclo)", "(segundo ciclo)"]


def build_loop_counting_finished_cycles(
    language_model: ThinkingLanguageModel | OfflineLanguageModel,
    budget: HourlyTokenBudget,
    finished_cycles: list[None],
) -> AutonomousLoop:
    return AutonomousLoop(
        lambda: Conversation(language_model, "You are a capybara."),
        budget,
        lambda: INNER_VOICE,
        INTERVAL_SECONDS,
        on_cycle_finished=lambda: finished_cycles.append(None),
    )


def test_tells_when_a_cycle_finished(
    language_model: ThinkingLanguageModel, budget: HourlyTokenBudget
) -> None:
    finished_cycles: list[None] = []
    loop = build_loop_counting_finished_cycles(language_model, budget, finished_cycles)

    loop.run_cycle()

    assert len(finished_cycles) == 1


def test_a_skipped_cycle_is_not_a_finished_cycle(
    language_model: ThinkingLanguageModel, budget: HourlyTokenBudget
) -> None:
    finished_cycles: list[None] = []
    loop = build_loop_counting_finished_cycles(language_model, budget, finished_cycles)
    budget.record(MAX_TOKENS_PER_HOUR)

    loop.run_cycle()

    assert finished_cycles == []


def build_loop_with_feelings(
    language_model: ThinkingLanguageModel,
    budget: HourlyTokenBudget,
    moments: list[str],
    sleeps: list[float],
    pace: float = 1.0,
) -> AutonomousLoop:
    def compose_inner_voice() -> str:
        moments.append("inner voice")
        return INNER_VOICE

    return AutonomousLoop(
        lambda: Conversation(language_model, "You are a capybara."),
        budget,
        compose_inner_voice,
        INTERVAL_SECONDS,
        sleep=sleeps.append,
        before_cycle=lambda: moments.append("self care"),
        pace=lambda: pace,
    )


def test_she_may_take_care_of_herself_before_thinking(
    language_model: ThinkingLanguageModel, budget: HourlyTokenBudget, sleeps: list[float]
) -> None:
    moments: list[str] = []
    loop = build_loop_with_feelings(language_model, budget, moments, sleeps)

    loop.run_cycle()

    assert moments == ["self care", "inner voice"]


def test_a_skipped_cycle_does_not_take_care_of_her(
    language_model: ThinkingLanguageModel, budget: HourlyTokenBudget, sleeps: list[float]
) -> None:
    moments: list[str] = []
    loop = build_loop_with_feelings(language_model, budget, moments, sleeps)
    budget.record(MAX_TOKENS_PER_HOUR)

    loop.run_cycle()

    assert moments == []


def test_her_pace_stretches_the_interval_between_cycles(
    language_model: ThinkingLanguageModel, budget: HourlyTokenBudget, sleeps: list[float]
) -> None:
    loop = build_loop_with_feelings(language_model, budget, [], sleeps, pace=1.5)

    loop.run(cycles=2)

    assert sleeps == [INTERVAL_SECONDS * 1.5]


def test_a_failed_cycle_is_not_a_finished_cycle(budget: HourlyTokenBudget) -> None:
    finished_cycles: list[None] = []
    loop = build_loop_counting_finished_cycles(OfflineLanguageModel(), budget, finished_cycles)

    loop.run_cycle()

    assert finished_cycles == []


@pytest.fixture
def recorded_spans() -> RecordedSpans:
    return RecordedSpans()


def traced_loop(
    language_model: ThinkingLanguageModel | OfflineLanguageModel,
    budget: HourlyTokenBudget,
    recorded_spans: RecordedSpans,
) -> AutonomousLoop:
    def start_conversation() -> Conversation:
        return Conversation(language_model, "You are a capybara.", tracer=recorded_spans.tracer)

    return AutonomousLoop(
        start_conversation,
        budget,
        lambda: INNER_VOICE,
        INTERVAL_SECONDS,
        sleep=lambda seconds: None,
        tracer=recorded_spans.tracer,
    )


def test_a_cycle_is_one_trace_with_the_inner_voice_and_the_thought(
    language_model: ThinkingLanguageModel,
    budget: HourlyTokenBudget,
    recorded_spans: RecordedSpans,
) -> None:
    traced_loop(language_model, budget, recorded_spans).run_cycle()

    cycle_span = recorded_spans.named("autonomous_cycle")
    attributes = dict(cycle_span.attributes or {})
    assert cycle_span.parent is None
    assert attributes["langfuse.observation.input"] == INNER_VOICE
    assert attributes["langfuse.observation.output"] == THOUGHT


def test_the_conversation_of_a_cycle_is_traced_inside_it(
    language_model: ThinkingLanguageModel,
    budget: HourlyTokenBudget,
    recorded_spans: RecordedSpans,
) -> None:
    traced_loop(language_model, budget, recorded_spans).run_cycle()

    turn_span = recorded_spans.named("conversation_turn")
    assert turn_span.parent is not None
    assert turn_span.parent.span_id == recorded_spans.named("autonomous_cycle").context.span_id


def test_a_failed_cycle_ends_its_span_as_an_error(
    budget: HourlyTokenBudget, recorded_spans: RecordedSpans
) -> None:
    traced_loop(OfflineLanguageModel(), budget, recorded_spans).run_cycle()

    cycle_span = recorded_spans.named("autonomous_cycle")
    assert cycle_span.status.status_code == StatusCode.ERROR
    assert cycle_span.status.description == "Ollama is not running"


def test_a_skipped_cycle_leaves_no_trace(
    language_model: ThinkingLanguageModel,
    budget: HourlyTokenBudget,
    recorded_spans: RecordedSpans,
) -> None:
    budget.record(MAX_TOKENS_PER_HOUR)

    traced_loop(language_model, budget, recorded_spans).run_cycle()

    assert recorded_spans.finished == ()
