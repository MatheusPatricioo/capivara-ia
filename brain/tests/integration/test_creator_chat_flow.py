"""Her creator types in the world and she answers there: a real WebSocket server on a free
local port, the event router, the worker thread and a fake language model."""

import json
from collections.abc import Iterator, Sequence

import pytest
from websockets.sync.client import ClientConnection, connect

from src.application.conversation import Conversation
from src.application.creator_presence import CreatorPresence
from src.capybara_chat import build_world_creator_chat, listen_to_creator
from src.domain.language_model import ChatMessage, Role, ToolDefinition
from src.infrastructure.serial_worker import SerialWorker
from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_server import WorldServer
from tests.integration.test_world_server import wait_until

LOCAL_HOST = "127.0.0.1"
ANY_FREE_PORT = 0
RECEIVE_TIMEOUT_SECONDS = 2.0
QUIET_SECONDS = 120.0
REPLY = "Oi, criador! Hoje eu li sobre **vaga-lumes**."


class ReplyingLanguageModel:
    def chat(
        self,
        messages: list[ChatMessage],
        tools: Sequence[ToolDefinition] = (),
    ) -> ChatMessage:
        return ChatMessage(Role.ASSISTANT, REPLY)


@pytest.fixture
def world_server() -> Iterator[WorldServer]:
    router = WorldEventRouter(on_noticed=lambda event: None)
    with (
        WorldServer(LOCAL_HOST, ANY_FREE_PORT, on_event=router.route) as server,
        SerialWorker("test-creator-chat") as worker,
    ):
        chat = build_world_creator_chat(
            Conversation(ReplyingLanguageModel(), "Você é uma capivara."),
            CreatorPresence(QUIET_SECONDS),
            server,
            heart=None,
        )
        router.when_creator_said(listen_to_creator(chat, worker))
        yield server


@pytest.fixture
def world(world_server: WorldServer) -> Iterator[ClientConnection]:
    with connect(f"ws://{LOCAL_HOST}:{world_server.port}") as connection:
        wait_until(lambda: world_server.client_count == 1)
        yield connection


@pytest.fixture
def messages_after_talking(world: ClientConnection) -> list[dict[str, object]]:
    world.send(json.dumps({"type": "creator_said", "text": "Oi, capivara!"}))
    return [json.loads(world.recv(timeout=RECEIVE_TIMEOUT_SECONDS)) for _ in range(3)]


def test_she_stops_to_listen_as_soon_as_her_creator_talks(
    messages_after_talking: list[dict[str, object]],
) -> None:
    assert messages_after_talking[0] == {"type": "listening", "seconds": QUIET_SECONDS}


def test_her_reply_renews_the_listening_time(
    messages_after_talking: list[dict[str, object]],
) -> None:
    assert messages_after_talking[1] == {"type": "listening", "seconds": QUIET_SECONDS}


def test_her_reply_arrives_as_a_clean_caption(
    messages_after_talking: list[dict[str, object]],
) -> None:
    assert messages_after_talking[2] == {
        "type": "speech",
        "speech_id": 1,
        "caption": "Oi, criador! Hoje eu li sobre vaga-lumes.",
    }
