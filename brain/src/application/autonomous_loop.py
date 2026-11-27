import logging
import time
from collections.abc import Callable

from opentelemetry import trace
from opentelemetry.trace import Tracer

from src.application import tracing
from src.application.conversation import Conversation, StepLimitReachedError
from src.application.token_budget import HourlyTokenBudget
from src.domain.language_model import LanguageModelError

logger = logging.getLogger(__name__)


def _ignore_thought(thought: str) -> None:
    pass


def _do_nothing() -> None:
    pass


def _steady_pace() -> float:
    return 1.0


class AutonomousLoop:
    """Wakes the capybara up from time to time so she decides on her own what to do.

    Each cycle starts a fresh conversation, so the history never grows without limit,
    and is skipped while the hourly token budget is spent. The inner voice is composed
    again every cycle, so it can carry what she learned in the previous ones.
    on_cycle_finished runs only after a cycle that really happened (not skipped, not failed).
    before_cycle runs before every cycle that is not skipped (she may take care of herself).
    pace multiplies the interval before the next cycle: above 1 when she is down and slow,
    below 1 when she is in a good tide.
    wait_for_turn runs first in every cycle and may block, like while her creator is
    talking with her: the conversation comes first.
    Every cycle that runs is one trace: a root span with everything she did inside it.
    Skipped cycles leave no trace, so a spent budget does not fill the panel with nothing.
    """

    def __init__(
        self,
        start_conversation: Callable[[], Conversation],
        budget: HourlyTokenBudget,
        compose_inner_voice: Callable[[], str],
        interval_seconds: float,
        on_thought: Callable[[str], None] = _ignore_thought,
        on_cycle_finished: Callable[[], None] = _do_nothing,
        sleep: Callable[[float], None] = time.sleep,
        before_cycle: Callable[[], None] = _do_nothing,
        pace: Callable[[], float] = _steady_pace,
        wait_for_turn: Callable[[], None] = _do_nothing,
        tracer: Tracer | None = None,
    ) -> None:
        self._start_conversation = start_conversation
        self._budget = budget
        self._compose_inner_voice = compose_inner_voice
        self._interval_seconds = interval_seconds
        self._on_thought = on_thought
        self._on_cycle_finished = on_cycle_finished
        self._sleep = sleep
        self._before_cycle = before_cycle
        self._pace = pace
        self._wait_for_turn = wait_for_turn
        self._tracer = tracer or trace.get_tracer(__name__)

    def run(self, cycles: int | None = None) -> None:
        """Runs the given number of cycles, or forever when cycles is None."""
        completed_cycles = 0
        while cycles is None or completed_cycles < cycles:
            if completed_cycles > 0:
                self._sleep(self._interval_seconds * self._pace())
            self.run_cycle()
            completed_cycles += 1

    def run_cycle(self) -> str | None:
        """Returns what the capybara thought, or None when the cycle was skipped or failed."""
        self._wait_for_turn()
        if not self._budget.has_room():
            logger.info(
                "Cycle skipped: %d tokens used in the last hour",
                self._budget.tokens_used_in_the_last_hour,
            )
            return None
        with self._tracer.start_as_current_span("autonomous_cycle") as span:
            span.set_attribute(tracing.OBSERVATION_TYPE, tracing.AGENT)
            span.set_attribute(tracing.AGENT_NAME, tracing.CAPYBARA_AGENT_NAME)
            return self._live_one_cycle(span)

    def _live_one_cycle(self, span: trace.Span) -> str | None:
        self._before_cycle()
        inner_voice = self._compose_inner_voice()
        tracing.record_input(span, inner_voice)
        try:
            thought = self._start_conversation().send(inner_voice)
        except (LanguageModelError, StepLimitReachedError) as error:
            logger.warning("Cycle failed: %s", error)
            tracing.mark_failed(span, str(error))
            return None
        tokens_used = self._budget.tokens_used_in_the_last_hour
        logger.info("Cycle finished (%d tokens in the last hour)", tokens_used)
        tracing.record_output(span, thought)
        tracing.record_metadata(span, "tokens_in_the_last_hour", tokens_used)
        self._on_cycle_finished()
        self._on_thought(thought)
        return thought
