import logging
import time
from collections.abc import Callable

from src.application.conversation import Conversation, StepLimitReachedError
from src.application.token_budget import HourlyTokenBudget
from src.domain.language_model import LanguageModelError

logger = logging.getLogger(__name__)


def _ignore_thought(thought: str) -> None:
    pass


def _do_nothing() -> None:
    pass


class AutonomousLoop:
    """Wakes the capybara up from time to time so she decides on her own what to do.

    Each cycle starts a fresh conversation, so the history never grows without limit,
    and is skipped while the hourly token budget is spent. The inner voice is composed
    again every cycle, so it can carry what she learned in the previous ones.
    on_cycle_finished runs only after a cycle that really happened (not skipped, not failed).
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
    ) -> None:
        self._start_conversation = start_conversation
        self._budget = budget
        self._compose_inner_voice = compose_inner_voice
        self._interval_seconds = interval_seconds
        self._on_thought = on_thought
        self._on_cycle_finished = on_cycle_finished
        self._sleep = sleep

    def run(self, cycles: int | None = None) -> None:
        """Runs the given number of cycles, or forever when cycles is None."""
        completed_cycles = 0
        while cycles is None or completed_cycles < cycles:
            if completed_cycles > 0:
                self._sleep(self._interval_seconds)
            self.run_cycle()
            completed_cycles += 1

    def run_cycle(self) -> str | None:
        """Returns what the capybara thought, or None when the cycle was skipped or failed."""
        if not self._budget.has_room():
            logger.info(
                "Cycle skipped: %d tokens used in the last hour",
                self._budget.tokens_used_in_the_last_hour,
            )
            return None
        try:
            thought = self._start_conversation().send(self._compose_inner_voice())
        except (LanguageModelError, StepLimitReachedError) as error:
            logger.warning("Cycle failed: %s", error)
            return None
        logger.info(
            "Cycle finished (%d tokens in the last hour)", self._budget.tokens_used_in_the_last_hour
        )
        self._on_cycle_finished()
        self._on_thought(thought)
        return thought
