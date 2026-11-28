"""Talks to a real WebSocket server on a free local port. No external service is involved."""

import json
import time
from collections.abc import Callable, Iterator

import pytest
from websockets.sync.client import ClientConnection, connect

from src.infrastructure.world_messages import GoToMessage, NoticedMessage, SkyMessage
from src.infrastructure.world_requests import DrawingListReply, WorldReply, WorldRequest
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
def received_events() -> list[NoticedMessage]:
    return []


@pytest.fixture
def server(received_events: list[NoticedMessage]) -> Iterator[WorldServer]:
    with WorldServer(LOCAL_HOST, ANY_FREE_PORT, on_event=received_events.append) as world_server:
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
    server.broadcast(
        SkyMessage(day_fraction=0.5, day_length_seconds=3600.0, weather="rain", moon_phase=0.5),
        remember=True,
    )

    with connect_world(server) as late_world:
        assert json.loads(late_world.recv(timeout=WAIT_TIMEOUT_SECONDS)) == {
            "type": "sky",
            "day_fraction": 0.5,
            "day_length_seconds": 3600.0,
            "weather": "rain",
            "moon_phase": 0.5,
        }


def test_broadcasting_without_any_world_does_not_fail(server: WorldServer) -> None:
    server.broadcast(GoToMessage(point="pond"))

    assert server.client_count == 0


def test_forgets_a_world_that_disconnected(server: WorldServer) -> None:
    with connect_world(server):
        wait_until(lambda: server.client_count == 1)

    wait_until(lambda: server.client_count == 0)


NOTICED_LILY = {"type": "noticed", "thing": "water_lily", "description": "uma vitória-régia"}


def test_hands_events_from_the_world_to_the_listener(
    world: ClientConnection, received_events: list[NoticedMessage]
) -> None:
    world.send(json.dumps(NOTICED_LILY))

    wait_until(lambda: len(received_events) == 1)
    assert received_events[0] == NoticedMessage(thing="water_lily", description="uma vitória-régia")


def test_drops_invalid_messages_and_keeps_listening_to_the_world(
    world: ClientConnection, received_events: list[NoticedMessage]
) -> None:
    world.send("not json at all")
    world.send(json.dumps(NOTICED_LILY))

    wait_until(lambda: len(received_events) == 1)
    assert received_events[0].thing == "water_lily"


def test_keeps_the_world_connected_when_the_listener_fails() -> None:
    def failing_listener(event: NoticedMessage) -> None:
        raise RuntimeError("listener bug")

    with WorldServer(LOCAL_HOST, ANY_FREE_PORT, on_event=failing_listener) as failing_server:
        with connect_world(failing_server) as world:
            wait_until(lambda: failing_server.client_count == 1)
            world.send(json.dumps(NOTICED_LILY))
            failing_server.broadcast(GoToMessage(point="pond"))

            assert json.loads(world.recv(timeout=WAIT_TIMEOUT_SECONDS))["point"] == "pond"


LIST_DRAWINGS = {"type": "list_drawings", "request_id": "r1"}


def answer_with_an_empty_gallery(request: WorldRequest) -> WorldReply:
    return DrawingListReply(request_id=request.request_id, folder_path="D:/x", drawings=[])


@pytest.fixture
def answering_server() -> Iterator[WorldServer]:
    with WorldServer(
        LOCAL_HOST, ANY_FREE_PORT, on_request=answer_with_an_empty_gallery
    ) as world_server:
        yield world_server


def test_answers_a_request_with_the_reply_of_the_handler(answering_server: WorldServer) -> None:
    with connect_world(answering_server) as world:
        world.send(json.dumps(LIST_DRAWINGS))

        reply = json.loads(world.recv(timeout=WAIT_TIMEOUT_SECONDS))

    assert reply == {
        "type": "drawing_list",
        "request_id": "r1",
        "folder_path": "D:/x",
        "drawings": [],
    }


def test_sends_the_reply_only_to_the_world_that_asked(answering_server: WorldServer) -> None:
    with connect_world(answering_server) as asking_world, connect_world(answering_server) as other:
        wait_until(lambda: answering_server.client_count == 2)
        asking_world.send(json.dumps(LIST_DRAWINGS))
        asking_world.recv(timeout=WAIT_TIMEOUT_SECONDS)

        with pytest.raises(TimeoutError):
            other.recv(timeout=0.2)


def test_a_request_is_not_handed_to_the_event_listener(
    server: WorldServer, world: ClientConnection, received_events: list[NoticedMessage]
) -> None:
    world.send(json.dumps(LIST_DRAWINGS))
    world.recv(timeout=WAIT_TIMEOUT_SECONDS)

    assert received_events == []


def test_without_a_handler_a_request_fails_as_not_found(world: ClientConnection) -> None:
    world.send(json.dumps(LIST_DRAWINGS))

    reply = json.loads(world.recv(timeout=WAIT_TIMEOUT_SECONDS))

    assert reply == {"type": "request_failed", "request_id": "r1", "reason": "not_found"}


def test_a_broken_request_fails_as_invalid(world: ClientConnection) -> None:
    world.send(json.dumps({"type": "get_drawing", "request_id": "r2", "id": "../brain/.env"}))

    reply = json.loads(world.recv(timeout=WAIT_TIMEOUT_SECONDS))

    assert reply == {"type": "request_failed", "request_id": "r2", "reason": "invalid_request"}


def test_a_failing_handler_answers_unreadable_and_keeps_the_world() -> None:
    def failing_handler(request: WorldRequest) -> WorldReply:
        raise RuntimeError("handler bug")

    with WorldServer(LOCAL_HOST, ANY_FREE_PORT, on_request=failing_handler) as failing_server:
        with connect_world(failing_server) as world:
            world.send(json.dumps(LIST_DRAWINGS))

            reply = json.loads(world.recv(timeout=WAIT_TIMEOUT_SECONDS))

    assert reply["reason"] == "unreadable"
