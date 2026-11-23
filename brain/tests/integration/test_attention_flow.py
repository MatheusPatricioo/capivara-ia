"""From the world to her attention: a real WebSocket server on a free local port."""

import json
import time
from collections.abc import Callable, Iterator

import pytest
from websockets.sync.client import ClientConnection, connect

from src.application.attention_inbox import AttentionInbox
from src.domain.attention import Attention, PointOfAttention
from src.infrastructure.world_server import WorldServer
from src.live_capybara import attention_listener

LOCAL_HOST = "127.0.0.1"
ANY_FREE_PORT = 0
WAIT_TIMEOUT_SECONDS = 2.0
LILIES_EVENT = {"type": "noticed", "thing": "water_lilies", "description": "vitórias-régias"}
MUSHROOMS_EVENT = {"type": "noticed", "thing": "mushrooms", "description": "cogumelos"}


def wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert condition(), "condition not met in time"


@pytest.fixture
def inbox() -> AttentionInbox:
    return AttentionInbox(Attention(capacity=5, rest_seconds=600.0))


@pytest.fixture
def world(inbox: AttentionInbox) -> Iterator[ClientConnection]:
    with WorldServer(LOCAL_HOST, ANY_FREE_PORT, on_event=attention_listener(inbox)) as server:
        with connect(f"ws://{LOCAL_HOST}:{server.port}") as connection:
            wait_until(lambda: server.client_count == 1)
            yield connection


def test_things_noticed_in_the_world_become_points_of_attention(
    world: ClientConnection, inbox: AttentionInbox
) -> None:
    world.send(json.dumps(LILIES_EVENT))
    world.send(json.dumps(MUSHROOMS_EVENT))

    wait_until(lambda: len(inbox.pending()) == 2)
    assert inbox.pending() == (
        PointOfAttention("mushrooms", "cogumelos"),
        PointOfAttention("water_lilies", "vitórias-régias"),
    )


def test_walking_by_the_same_thing_again_keeps_one_point_of_attention(
    world: ClientConnection, inbox: AttentionInbox
) -> None:
    world.send(json.dumps(LILIES_EVENT))
    world.send(json.dumps(LILIES_EVENT))
    world.send(json.dumps(MUSHROOMS_EVENT))

    wait_until(lambda: len(inbox.pending()) == 2)
    assert [point.thing_id for point in inbox.pending()] == ["mushrooms", "water_lilies"]
