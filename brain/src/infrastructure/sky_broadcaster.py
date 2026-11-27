import logging
import threading
from types import TracebackType
from typing import Self

from src.application.world_sky import WorldSky
from src.infrastructure.websocket_body import MessageBroadcaster
from src.infrastructure.world_messages import sky_message

logger = logging.getLogger(__name__)


class SkyBroadcaster:
    """Tells the world the time of day and the weather, every interval_seconds.

    It runs in its own thread, because the agent loop can spend minutes in one cycle.
    The message is remembered, so a world opened later gets the sky right away. Between
    messages the world moves the sun on its own; each message only corrects it.
    """

    def __init__(
        self, sky: WorldSky, broadcaster: MessageBroadcaster, interval_seconds: float
    ) -> None:
        self._sky = sky
        self._broadcaster = broadcaster
        self._interval_seconds = interval_seconds
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    def publish(self) -> None:
        self._broadcaster.broadcast(sky_message(self._sky.look()), remember=True)

    def start(self) -> None:
        self.publish()
        self._thread = threading.Thread(target=self._keep_publishing, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

    def _keep_publishing(self) -> None:
        while not self._stopping.wait(self._interval_seconds):
            try:
                self.publish()
            except Exception:
                # A bad moment must not stop the sky for the rest of her life.
                logger.exception("Failed to publish the sky")
