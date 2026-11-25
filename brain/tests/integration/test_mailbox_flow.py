"""The mailbox over a real WebSocket: the world gets the letters and opens one."""

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from websockets.sync.client import ClientConnection, connect

from src.application.shown_mailbox import ShownMailbox
from src.domain.letter import Letter
from src.infrastructure.markdown_mailbox import MarkdownMailbox
from src.infrastructure.websocket_mailbox_display import WebSocketMailboxDisplay
from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_server import WorldServer

LOCAL_HOST = "127.0.0.1"
ANY_FREE_PORT = 0
WAIT_TIMEOUT_SECONDS = 2.0
LETTER = Letter(datetime(2026, 11, 25, 14, 30), "Oi, Matheus! Senti sua falta.")


def ignore_noticed(event: object) -> None:
    pass


@pytest.fixture
def router() -> WorldEventRouter:
    return WorldEventRouter(on_noticed=ignore_noticed)


@pytest.fixture
def server(router: WorldEventRouter) -> Iterator[WorldServer]:
    with WorldServer(LOCAL_HOST, ANY_FREE_PORT, on_event=router.route) as world_server:
        yield world_server


@pytest.fixture
def mailbox(server: WorldServer, router: WorldEventRouter, tmp_path: Path) -> ShownMailbox:
    shown_mailbox = ShownMailbox(MarkdownMailbox(tmp_path), WebSocketMailboxDisplay(server))
    router.when_letter_opened(shown_mailbox.open_letter)
    return shown_mailbox


def next_mailbox(world: ClientConnection) -> list[dict[str, object]]:
    message = json.loads(world.recv(timeout=WAIT_TIMEOUT_SECONDS))
    assert message["type"] == "mailbox"
    letters: list[dict[str, object]] = message["letters"]
    return letters


def test_a_world_that_connects_later_finds_the_unread_letter(
    server: WorldServer, mailbox: ShownMailbox
) -> None:
    mailbox.post(LETTER)

    with connect(f"ws://{LOCAL_HOST}:{server.port}") as world:
        letters = next_mailbox(world)

    assert (letters[0]["text"], letters[0]["unread"]) == (LETTER.text, True)


def test_opening_a_letter_in_the_world_marks_it_as_read(
    server: WorldServer, mailbox: ShownMailbox
) -> None:
    file_name = mailbox.post(LETTER)

    with connect(f"ws://{LOCAL_HOST}:{server.port}") as world:
        next_mailbox(world)
        world.send(json.dumps({"type": "letter_opened", "letter": file_name}))
        letters = next_mailbox(world)

    assert letters[0]["unread"] is False
