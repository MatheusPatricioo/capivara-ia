"""Her creator holds the talk button in the world and speaks: a real WebSocket server on a
free local port, the router, the worker thread, fake ears and a fake language model."""

import json
from collections.abc import Iterator, Sequence

import pytest
from websockets.sync.client import connect

from src.application.conversation import Conversation
from src.application.creator_ears import CreatorEars
from src.application.creator_presence import CreatorPresence
from src.capybara_chat import build_world_creator_chat, listen_to_creator_voice
from src.domain.language_model import ChatMessage, Role, ToolDefinition
from src.domain.speech import SpokenAudio
from src.infrastructure.serial_worker import SerialWorker
from src.infrastructure.websocket_conversation_display import WebSocketConversationDisplay
from src.infrastructure.world_event_router import WorldEventRouter
from src.infrastructure.world_server import WorldServer
from tests.integration.test_world_server import wait_until

LOCAL_HOST = "127.0.0.1"
ANY_FREE_PORT = 0
RECEIVE_TIMEOUT_SECONDS = 2.0
QUIET_SECONDS = 120.0
HEARD_TEXT = "Oi, capivara!"
REPLY = "Oi, criador!"
RECORDING = SpokenAudio(b"\x01\x00\x02\x00", 16000)


class ReplyingLanguageModel:
    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        return ChatMessage(Role.ASSISTANT, REPLY)


class ReadyMicrophone:
    def start_recording(self) -> None:
        pass

    def stop_recording(self) -> SpokenAudio:
        return RECORDING


class FixedRecognizer:
    def __init__(self, text: str) -> None:
        self._text = text

    def transcribe(self, audio: SpokenAudio) -> str:
        return self._text


def serve_world_with_ears(heard_text: str) -> Iterator[WorldServer]:
    router = WorldEventRouter(on_noticed=lambda event: None)
    with (
        WorldServer(LOCAL_HOST, ANY_FREE_PORT, on_event=router.route) as server,
        SerialWorker("test-creator-voice") as worker,
    ):
        chat = build_world_creator_chat(
            Conversation(ReplyingLanguageModel(), "Você é uma capivara."),
            CreatorPresence(QUIET_SECONDS),
            server,
            heart=None,
        )
        ears = CreatorEars(ReadyMicrophone(), FixedRecognizer(heard_text))
        router.when_creator_talking(
            listen_to_creator_voice(chat, worker, ears, WebSocketConversationDisplay(server))
        )
        yield server


def talk_and_collect(server: WorldServer, count: int) -> list[dict[str, object]]:
    with connect(f"ws://{LOCAL_HOST}:{server.port}") as world:
        wait_until(lambda: server.client_count == 1)
        world.send(json.dumps({"type": "creator_talking", "talking": True}))
        world.send(json.dumps({"type": "creator_talking", "talking": False}))
        return [json.loads(world.recv(timeout=RECEIVE_TIMEOUT_SECONDS)) for _ in range(count)]


@pytest.fixture
def world_that_understands() -> Iterator[WorldServer]:
    yield from serve_world_with_ears(HEARD_TEXT)


@pytest.fixture
def world_that_hears_nothing() -> Iterator[WorldServer]:
    yield from serve_world_with_ears("")


def test_she_stops_to_listen_when_he_presses_the_button(
    world_that_understands: WorldServer,
) -> None:
    messages = talk_and_collect(world_that_understands, 4)

    assert messages[0] == {"type": "listening", "seconds": QUIET_SECONDS}


def test_the_world_is_told_what_she_understood(world_that_understands: WorldServer) -> None:
    messages = talk_and_collect(world_that_understands, 4)

    assert messages[1] == {"type": "heard", "text": HEARD_TEXT}


def test_she_answers_what_he_said_out_loud(world_that_understands: WorldServer) -> None:
    messages = talk_and_collect(world_that_understands, 4)

    assert messages[3] == {"type": "speech", "speech_id": 1, "caption": REPLY, "audio": None}


def test_hearing_nothing_is_told_to_the_world(world_that_hears_nothing: WorldServer) -> None:
    messages = talk_and_collect(world_that_hears_nothing, 2)

    assert messages[1] == {"type": "heard", "text": ""}
