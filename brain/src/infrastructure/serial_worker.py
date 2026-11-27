import logging
import queue
import threading
from collections.abc import Callable
from types import TracebackType
from typing import Self

logger = logging.getLogger(__name__)

Task = Callable[[], None]


class SerialWorker:
    """Runs submitted tasks one at a time, in order, on its own thread.

    The world server thread must keep reading messages, so it cannot wait seconds for the
    language model: it submits the work here and goes back to listening. A queue keeps
    the order, and a single thread means two replies are never written at the same time.
    """

    def __init__(self, name: str) -> None:
        self._tasks: queue.Queue[Task | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run_tasks, name=name, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        """Finishes the tasks already submitted, then stops. None is the signal to stop."""
        self._tasks.put(None)
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

    def submit(self, task: Task) -> None:
        self._tasks.put(task)

    def _run_tasks(self) -> None:
        while (task := self._tasks.get()) is not None:
            try:
                task()
            except Exception:
                # One failed task must not stop the ones after it.
                logger.exception("A background task failed")
