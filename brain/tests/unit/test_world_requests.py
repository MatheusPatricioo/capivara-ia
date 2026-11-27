import json

import pytest
from pydantic import BaseModel

from src.infrastructure.world_requests import (
    MAX_REQUEST_ID_LENGTH,
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
    invalid_request_reply,
    parse_world_reply,
    parse_world_request,
)


@pytest.fixture
def cat_note() -> SavedItemSummary:
    return SavedItemSummary(
        id="2026-11-23-gato-dormindo.md", title="gato dormindo", saved_at="2026-11-23T10:15"
    )


@pytest.fixture
def cat_drawing() -> SavedItemSummary:
    return SavedItemSummary(
        id="2026-11-23-gato-dormindo.png", title="gato dormindo", saved_at="2026-11-23T10:20"
    )


@pytest.mark.parametrize(
    "request_message",
    [
        ListDiscoveriesRequest(request_id="r1", folder="discoveries"),
        ListDiscoveriesRequest(request_id="r2", folder="suggestions"),
        GetDiscoveryRequest(request_id="r3", folder="discoveries", id="2026-11-23-gato.md"),
        ListDrawingsRequest(request_id="r4"),
        GetDrawingRequest(request_id="r5", id="2026-11-23-gato.png"),
        GetSearchHistoryRequest(request_id="r6"),
    ],
)
def test_a_request_survives_the_round_trip_through_json(request_message: BaseModel) -> None:
    assert parse_world_request(request_message.model_dump_json()) == request_message


def test_parses_a_request_written_by_hand_like_godot_does() -> None:
    payload = '{"type": "get_drawing", "request_id": "draw-7", "id": "2026-11-23-gato.png"}'

    assert parse_world_request(payload) == GetDrawingRequest(
        request_id="draw-7", id="2026-11-23-gato.png"
    )


@pytest.mark.parametrize(
    "unsafe_id",
    ["../brain/.env", "sub/2026-11-23-gato.md", "..\\segredo.md", "gato", "gato..md", ""],
)
def test_rejects_an_id_that_could_leave_the_folder(unsafe_id: str) -> None:
    payload = json.dumps({"type": "get_drawing", "request_id": "r1", "id": unsafe_id})

    assert parse_world_request(payload) is None


def test_rejects_a_folder_that_is_not_one_of_hers() -> None:
    payload = '{"type": "list_discoveries", "request_id": "r1", "folder": "history"}'

    assert parse_world_request(payload) is None


def test_rejects_a_request_without_request_id() -> None:
    assert parse_world_request('{"type": "list_drawings"}') is None


def test_rejects_a_request_id_longer_than_the_limit() -> None:
    long_id = "a" * (MAX_REQUEST_ID_LENGTH + 1)

    assert parse_world_request(json.dumps({"type": "list_drawings", "request_id": long_id})) is None


def test_rejects_a_request_of_unknown_type() -> None:
    assert parse_world_request('{"type": "delete_drawing", "request_id": "r1"}') is None


def test_an_event_is_not_mistaken_for_a_request() -> None:
    assert parse_world_request('{"type": "creator_said", "text": "oi"}') is None


def test_discovery_list_survives_the_round_trip(cat_note: SavedItemSummary) -> None:
    reply = DiscoveryListReply(
        request_id="r1",
        folder="discoveries",
        folder_path="D:/capivara-descobertas",
        discoveries=[cat_note],
    )

    assert parse_world_reply(reply.model_dump_json()) == reply


def test_discovery_survives_the_round_trip() -> None:
    reply = DiscoveryReply(
        request_id="r2",
        folder="suggestions",
        id="2026-11-23-lousa-maior.md",
        title="lousa maior",
        markdown="# Lousa maior\n\nUma lousa maior ajudaria.",
    )

    assert parse_world_reply(reply.model_dump_json()) == reply


def test_drawing_list_survives_the_round_trip(cat_drawing: SavedItemSummary) -> None:
    reply = DrawingListReply(
        request_id="r3", folder_path="D:/capivara-descobertas", drawings=[cat_drawing]
    )

    assert parse_world_reply(reply.model_dump_json()) == reply


def test_drawing_survives_the_round_trip() -> None:
    reply = DrawingReply(
        request_id="r4", id="2026-11-23-gato.png", title="gato", png_base64="iVBORw0KGgo="
    )

    assert parse_world_reply(reply.model_dump_json()) == reply


def test_search_history_survives_the_round_trip() -> None:
    search = SearchEntry(
        searched_at="2026-11-23T09:00",
        query="capivaras dormem quanto",
        pages=[FoundPage(title="Capivara", url="https://pt.wikipedia.org/wiki/Capivara")],
    )
    reply = SearchHistoryReply(request_id="r5", searches=[search])

    assert parse_world_reply(reply.model_dump_json()) == reply


def test_failure_survives_the_round_trip() -> None:
    reply = RequestFailedReply(request_id="r6", reason="not_found")

    assert parse_world_reply(reply.model_dump_json()) == reply


def test_drawing_reply_is_not_valid_without_the_image() -> None:
    payload = (
        '{"type": "drawing", "request_id": "r1", "id": "a.png", "title": "a", "png_base64": ""}'
    )

    assert parse_world_reply(payload) is None


def test_reply_json_has_its_type_for_the_client_to_dispatch(cat_drawing: SavedItemSummary) -> None:
    reply = DrawingListReply(request_id="r1", folder_path="D:/x", drawings=[cat_drawing])

    assert json.loads(reply.model_dump_json())["type"] == "drawing_list"


def test_a_broken_request_gets_a_failure_with_its_request_id() -> None:
    payload = '{"type": "get_drawing", "request_id": "r9", "id": "../brain/.env"}'

    assert invalid_request_reply(payload) == RequestFailedReply(
        request_id="r9", reason="invalid_request"
    )


def test_a_broken_request_without_a_valid_request_id_gets_no_failure() -> None:
    assert invalid_request_reply('{"type": "get_drawing", "request_id": "../x"}') is None


def test_an_event_gets_no_failure() -> None:
    assert invalid_request_reply('{"type": "creator_said", "text": "oi"}') is None


def test_a_payload_that_is_not_json_gets_no_failure() -> None:
    assert invalid_request_reply("not json") is None


def test_a_listed_item_is_not_done_unless_told(cat_note: SavedItemSummary) -> None:
    assert cat_note.done is False
