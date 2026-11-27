"""Real messages, made by the Pydantic models, checked against the committed JSON Schema.

test_protocol_schema.py proves the schema files are up to date; this proves they describe the
messages truly: any client that validates with docs/protocol accepts what the brain sends and
sends what the brain accepts.
"""

import json
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel

from src.domain.speech import VoiceMode
from src.export_protocol_schema import PROTOCOL_DOCS_DIR
from src.infrastructure.protocol_schema import BRAIN_TO_WORLD_FILE_NAME, WORLD_TO_BRAIN_FILE_NAME
from src.infrastructure.world_messages import (
    ConversationEndedMessage,
    CreatorSaidMessage,
    CreatorTalkingMessage,
    DiaryDayMessage,
    DiaryEntryMessage,
    DiaryMessage,
    FeelingsMessage,
    GoToMessage,
    HeardMessage,
    LetterMessage,
    LetterOpenedMessage,
    LetterRepliedMessage,
    ListeningMessage,
    MailboxMessage,
    NoticedMessage,
    SkyMessage,
    SpeechAudio,
    SpeechMessage,
    VoiceModeMessage,
)
from src.infrastructure.world_requests import (
    DiscoveryListReply,
    DiscoveryReply,
    DrawingListReply,
    DrawingReply,
    FoundPage,
    GetDiscoveryRequest,
    GetDrawingRequest,
    GetSearchHistoryRequest,
    ListDiscoveriesRequest,
    ListDrawingsRequest,
    RequestFailedReply,
    SavedItemSummary,
    SearchEntry,
    SearchHistoryReply,
)

CAT_DRAWING = SavedItemSummary(id="2026-11-23-gato.png", title="gato", saved_at="2026-11-23T10:20")

BRAIN_TO_WORLD_SAMPLES: list[BaseModel] = [
    GoToMessage(point="computer"),
    FeelingsMessage(emotion="joy", intensity=0.7, valence=0.5, arousal=0.4),
    SkyMessage(day_fraction=0.5, day_length_seconds=86400.0, weather="clear"),
    MailboxMessage(
        letters=[
            LetterMessage(
                file_name="2026-11-25-saudade.md",
                written_at="2026-11-25T14:30",
                text="Oi, criador!",
                unread=False,
                replied_at="2026-11-25T15:00",
                reply="Oi, capivara!",
            )
        ]
    ),
    DiaryMessage(
        days=[
            DiaryDayMessage(
                day="2026-11-25",
                entries=[
                    DiaryEntryMessage(written_at="2026-11-25T14:30", text="Li sobre vaga-lumes.")
                ],
                mood="um dia bom",
            )
        ]
    ),
    ListeningMessage(seconds=10.0),
    SpeechMessage(
        speech_id=1, caption="Oi!", audio=SpeechAudio(sample_rate=22050, pcm16_base64="AAAA")
    ),
    SpeechMessage(speech_id=2, caption="Sem voz."),
    HeardMessage(text=""),
    DiscoveryListReply(
        request_id="world-1",
        folder="discoveries",
        folder_path="D:/capivara-descobertas",
        discoveries=[
            SavedItemSummary(id="2026-11-23-gato.md", title="Gato", saved_at="2026-11-23T10:15")
        ],
    ),
    DiscoveryReply(
        request_id="world-2",
        folder="suggestions",
        id="2026-11-23-lousa.md",
        title="Lousa maior",
        markdown="# Lousa maior\n",
    ),
    DrawingListReply(request_id="world-3", folder_path="D:/x", drawings=[CAT_DRAWING]),
    DrawingReply(request_id="world-4", id="2026-11-23-gato.png", title="gato", png_base64="iVBO"),
    SearchHistoryReply(
        request_id="world-5",
        searches=[
            SearchEntry(
                searched_at="2026-11-23T09:00",
                query="capivaras",
                pages=[FoundPage(title="Capivara", url="https://pt.wikipedia.org/wiki/Capivara")],
            )
        ],
    ),
    RequestFailedReply(request_id="world-6", reason="not_found"),
]

WORLD_TO_BRAIN_SAMPLES: list[BaseModel] = [
    NoticedMessage(thing="water_lily", description="uma vitória-régia"),
    LetterOpenedMessage(letter="2026-11-25-saudade.md"),
    LetterRepliedMessage(letter="2026-11-25-saudade.md", text="Também senti saudade."),
    CreatorSaidMessage(text="Oi, capivara!"),
    VoiceModeMessage(mode=VoiceMode.MUTE),
    CreatorTalkingMessage(talking=True),
    ConversationEndedMessage(),
    ListDiscoveriesRequest(request_id="world-1", folder="suggestions"),
    GetDiscoveryRequest(request_id="world-2", folder="discoveries", id="2026-11-23-gato.md"),
    ListDrawingsRequest(request_id="world-3"),
    GetDrawingRequest(request_id="world-4", id="2026-11-23-gato.png"),
    GetSearchHistoryRequest(request_id="world-5"),
]


def load_schema(file_name: str) -> dict[str, Any]:
    schema: dict[str, Any] = json.loads((PROTOCOL_DOCS_DIR / file_name).read_text(encoding="utf-8"))
    return schema


def as_sent(message: BaseModel) -> dict[str, Any]:
    """The message exactly as it travels on the WebSocket."""
    sent: dict[str, Any] = json.loads(message.model_dump_json())
    return sent


def sample_types(samples: list[BaseModel]) -> set[str]:
    return {as_sent(sample)["type"] for sample in samples}


@pytest.fixture(scope="module")
def brain_to_world() -> Draft202012Validator:
    return Draft202012Validator(load_schema(BRAIN_TO_WORLD_FILE_NAME))


@pytest.fixture(scope="module")
def world_to_brain() -> Draft202012Validator:
    return Draft202012Validator(load_schema(WORLD_TO_BRAIN_FILE_NAME))


@pytest.mark.parametrize("file_name", [BRAIN_TO_WORLD_FILE_NAME, WORLD_TO_BRAIN_FILE_NAME])
def test_the_schema_file_is_a_valid_json_schema(file_name: str) -> None:
    Draft202012Validator.check_schema(load_schema(file_name))


def test_every_brain_message_type_has_a_sample() -> None:
    schema_types = set(load_schema(BRAIN_TO_WORLD_FILE_NAME)["discriminator"]["mapping"])

    assert sample_types(BRAIN_TO_WORLD_SAMPLES) == schema_types


def test_every_world_message_type_has_a_sample() -> None:
    schema_types = set(load_schema(WORLD_TO_BRAIN_FILE_NAME)["discriminator"]["mapping"])

    assert sample_types(WORLD_TO_BRAIN_SAMPLES) == schema_types


@pytest.mark.parametrize("message", BRAIN_TO_WORLD_SAMPLES, ids=lambda sample: sample.type)
def test_what_the_brain_sends_follows_the_contract(
    message: BaseModel, brain_to_world: Draft202012Validator
) -> None:
    brain_to_world.validate(as_sent(message))


@pytest.mark.parametrize("message", WORLD_TO_BRAIN_SAMPLES, ids=lambda sample: sample.type)
def test_what_the_brain_accepts_follows_the_contract(
    message: BaseModel, world_to_brain: Draft202012Validator
) -> None:
    world_to_brain.validate(as_sent(message))


def test_the_contract_rejects_a_message_without_type(world_to_brain: Draft202012Validator) -> None:
    assert world_to_brain.is_valid({"request_id": "world-1"}) is False


def test_the_contract_rejects_an_unknown_type(world_to_brain: Draft202012Validator) -> None:
    assert world_to_brain.is_valid({"type": "delete_drawing", "request_id": "world-1"}) is False


def test_the_contract_rejects_a_request_without_request_id(
    world_to_brain: Draft202012Validator,
) -> None:
    assert world_to_brain.is_valid({"type": "list_drawings"}) is False


def test_the_contract_rejects_an_id_that_could_leave_the_folder(
    world_to_brain: Draft202012Validator,
) -> None:
    request = {"type": "get_drawing", "request_id": "world-1", "id": "../brain/.env"}

    assert world_to_brain.is_valid(request) is False


def test_the_contract_rejects_a_speech_without_caption(
    brain_to_world: Draft202012Validator,
) -> None:
    assert brain_to_world.is_valid({"type": "speech", "speech_id": 1, "caption": ""}) is False
