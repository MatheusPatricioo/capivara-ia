import logging
import threading

import pytest

from src.infrastructure.serial_worker import SerialWorker


def test_runs_the_tasks_in_the_order_they_were_submitted() -> None:
    finished: list[int] = []

    with SerialWorker("test-worker") as worker:
        for number in range(5):
            worker.submit(lambda number=number: finished.append(number))

    assert finished == [0, 1, 2, 3, 4]


def test_runs_the_tasks_outside_the_thread_that_submits_them() -> None:
    task_threads: list[threading.Thread] = []

    with SerialWorker("test-worker") as worker:
        worker.submit(lambda: task_threads.append(threading.current_thread()))

    assert task_threads[0] is not threading.current_thread()


def test_a_failed_task_does_not_stop_the_next_one(caplog: pytest.LogCaptureFixture) -> None:
    finished: list[str] = []

    def fail() -> None:
        raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR), SerialWorker("test-worker") as worker:
        worker.submit(fail)
        worker.submit(lambda: finished.append("next"))

    assert finished == ["next"]
