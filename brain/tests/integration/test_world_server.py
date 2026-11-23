"""Talks to a real WebSocket server on a free local port. No external service is involved."""

import json
import time
from collections.abc import Callable, Iterator

import pytest
from websockets.sync.client import ClientConnection, connect

from src.infrastructure.world_messages import GoToMessage, chalkboard_message
from src.infrastructure.world_server import WorldServer

LOCAL_HOST = "127.0.0.1"
ANY_FREE_PORT = 0
WAIT_TIMEOUT_SECONDS = 2.0


def wait_until(condition: Callable[[], bool]) -> None:
    """The server registers clients in its own thread, so tests wait for it a little."""
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert condition(), "condition not met in time"


@pytest.fixture
def server() -> Iterator[WorldServer]:
    with WorldServer(LOCAL_HOST, ANY_FREE_PORT) as world_server:
        yield world_server


def connect_world(server: WorldServer) -> ClientConnection:
    return connect(f"ws://{LOCAL_HOST}:{server.port}")


@pytest.fixture
def world(server: WorldServer) -> Iterator[ClientConnection]:
    with connect_world(server) as connection:
        wait_until(lambda: server.client_count == 1)
        yield connection


def test_sends_a_broadcast_message_to_the_connected_world(
    server: WorldServer, world: ClientConnection
) -> None:
    server.broadcast(GoToMessage(point="computer"))

    assert json.loads(world.recv(timeout=WAIT_TIMEOUT_SECONDS)) == {
        "type": "go_to",
        "point": "computer",
    }


def test_replays_remembered_messages_to_a_world_that_connects_later(server: WorldServer) -> None:
    server.broadcast(chalkboard_message(()), remember=True)

    with connect_world(server) as late_world:
        assert json.loads(late_world.recv(timeout=WAIT_TIMEOUT_SECONDS)) == {
            "type": "chalkboard",
            "drawings": [],
        }


def test_broadcasting_without_any_world_does_not_fail(server: WorldServer) -> None:
    server.broadcast(GoToMessage(point="pond"))

    assert server.client_count == 0


def test_forgets_a_world_that_disconnected(server: WorldServer) -> None:
    with connect_world(server):
        wait_until(lambda: server.client_count == 1)

    wait_until(lambda: server.client_count == 0)
