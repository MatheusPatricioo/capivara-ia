import logging
import random
import time
from collections.abc import Callable
from typing import Protocol

from src.domain.body import Body
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.behavior import comfort_place
from src.domain.feelings.emotional_life import EmotionalLife

DEFAULT_REST_SECONDS = 30 * 60.0
"""After taking care of herself, she waits a while before doing it again."""

logger = logging.getLogger(__name__)


class SelfCareHeart(Protocol):
    def check_in(self, pending_wishes: int | None = None) -> EmotionalLife: ...

    def feel(self, event: EmotionalEvent) -> EmotionalLife: ...


class SelfCare:
    """When she needs it, she walks to a comfort place (pond, food bowl, dog house).

    It is coping, not a cure: it soothes frustration and sadness and refills comfort, but
    missing her creator only ends when he comes back.
    """

    def __init__(
        self,
        heart: SelfCareHeart,
        body: Body,
        rng: random.Random | None = None,
        rest_seconds: float = DEFAULT_REST_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._heart = heart
        self._body = body
        self._rng = rng or random.Random()
        self._rest_seconds = rest_seconds
        self._clock = clock
        self._last_care_at: float | None = None

    def take_care(self) -> None:
        if self._is_resting():
            return
        place = comfort_place(self._heart.check_in(), self._rng)
        if place is None:
            return
        logger.info("She went to the %s to take care of herself", place.value)
        self._body.go_to(place)
        self._heart.feel(EmotionalEvent(EventKind.VISITED_COMFORT_PLACE))
        self._last_care_at = self._clock()

    def _is_resting(self) -> bool:
        return (
            self._last_care_at is not None
            and self._clock() - self._last_care_at < self._rest_seconds
        )
