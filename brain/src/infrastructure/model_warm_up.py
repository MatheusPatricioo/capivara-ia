"""Loads her model while the brain starts, so her creator's first message is not the one
that waits for the model to come from the disk."""

import logging
import threading
import time
from collections.abc import Callable
from typing import Protocol

from src.domain.language_model import LanguageModelError

logger = logging.getLogger(__name__)

THREAD_NAME = "model-warm-up"


class WarmableModel(Protocol):
    def warm_up(self) -> None: ...


def warm_up_in_background(
    model: WarmableModel, clock: Callable[[], float] = time.monotonic
) -> threading.Thread:
    """Starts loading the model in a daemon thread and returns it at once.

    A failure is only logged: the model then loads on the first real call, as before.
    """
    thread = threading.Thread(target=_warm_up, args=(model, clock), name=THREAD_NAME, daemon=True)
    thread.start()
    return thread


def _warm_up(model: WarmableModel, clock: Callable[[], float]) -> None:
    started_at = clock()
    try:
        model.warm_up()
    except LanguageModelError as error:
        logger.warning("Could not load her model ahead of time: %s", error)
        return
    logger.info("Her model is loaded and ready (%.1fs)", clock() - started_at)
