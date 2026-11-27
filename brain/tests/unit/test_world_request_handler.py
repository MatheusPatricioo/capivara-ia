import base64
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.domain.search_log import FoundPage, SearchRecord
from src.infrastructure.jsonl_search_log import JsonlSearchLog
from src.infrastructure.saved_files_reader import SavedFilesReader
from src.infrastructure.world_request_handler import WorldRequestHandler
from src.infrastructure.world_requests import (
    DiscoveryListReply,
    DiscoveryReply,
    DrawingListReply,
    DrawingReply,
    GetDiscoveryRequest,
    GetDrawingRequest,
    GetSearchHistoryRequest,
    ListDiscoveriesRequest,
    ListDrawingsRequest,
    RequestFailedReply,
    SearchHistoryReply,
)

CHANGED_AT = datetime(2026, 11, 23, 14, 30).timestamp()
SUN_PNG = b"\x89PNG sun"
FIREFLY_NOTE = "# Vaga-lumes à noite\n\nPiscam para se encontrar.\n"
MOON_SEARCH = SearchRecord(
    searched_at=datetime(2026, 11, 23, 10, 15, 2, tzinfo=timezone(timedelta(hours=-3))),
    query="fases da lua",
    results=(FoundPage(title="Fases da Lua", url="https://example.com/lua"),),
)


@pytest.fixture
def discoveries_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "descobertas"
    folder.mkdir()
    note_file = folder / "2026-11-23-vaga-lumes.md"
    note_file.write_text(FIREFLY_NOTE, encoding="utf-8")
    drawing_file = folder / "2026-11-23-sol.png"
    drawing_file.write_bytes(SUN_PNG)
    for saved_file in (note_file, drawing_file):
        os.utime(saved_file, (CHANGED_AT, CHANGED_AT))
    return folder


@pytest.fixture
def search_log(discoveries_dir: Path) -> JsonlSearchLog:
    log = JsonlSearchLog(discoveries_dir / "history" / "searches.jsonl")
    log.append(MOON_SEARCH)
    return log


@pytest.fixture
def handler(discoveries_dir: Path, search_log: JsonlSearchLog) -> WorldRequestHandler:
    return WorldRequestHandler(SavedFilesReader(discoveries_dir), search_log)


def test_lists_the_discoveries_with_ready_titles(handler: WorldRequestHandler) -> None:
    reply = handler.handle(ListDiscoveriesRequest(request_id="r1", folder="discoveries"))

    assert isinstance(reply, DiscoveryListReply)
    assert [(item.id, item.title) for item in reply.discoveries] == [
        ("2026-11-23-vaga-lumes.md", "Vaga-lumes à noite")
    ]


def test_a_listed_item_carries_its_date_in_the_world_format(handler: WorldRequestHandler) -> None:
    reply = handler.handle(ListDiscoveriesRequest(request_id="r1", folder="discoveries"))

    assert isinstance(reply, DiscoveryListReply)
    assert reply.discoveries[0].saved_at == "2026-11-23T14:30"


def test_the_list_tells_where_the_folder_is(
    handler: WorldRequestHandler, discoveries_dir: Path
) -> None:
    reply = handler.handle(ListDiscoveriesRequest(request_id="r1", folder="suggestions"))

    assert isinstance(reply, DiscoveryListReply)
    assert reply.folder_path == (discoveries_dir / "sugestoes").resolve().as_posix()


def test_answers_with_the_same_request_id(handler: WorldRequestHandler) -> None:
    reply = handler.handle(ListDrawingsRequest(request_id="pedido-42"))

    assert reply.request_id == "pedido-42"


def test_gives_the_markdown_of_a_discovery(handler: WorldRequestHandler) -> None:
    request = GetDiscoveryRequest(
        request_id="r2", folder="discoveries", id="2026-11-23-vaga-lumes.md"
    )

    assert handler.handle(request) == DiscoveryReply(
        request_id="r2",
        folder="discoveries",
        id="2026-11-23-vaga-lumes.md",
        title="Vaga-lumes à noite",
        markdown=FIREFLY_NOTE,
    )


def test_lists_the_drawings_without_their_images(handler: WorldRequestHandler) -> None:
    reply = handler.handle(ListDrawingsRequest(request_id="r3"))

    assert isinstance(reply, DrawingListReply)
    assert [(item.id, item.title) for item in reply.drawings] == [("2026-11-23-sol.png", "sol")]


def test_gives_a_drawing_as_base64(handler: WorldRequestHandler) -> None:
    reply = handler.handle(GetDrawingRequest(request_id="r4", id="2026-11-23-sol.png"))

    assert isinstance(reply, DrawingReply)
    assert base64.b64decode(reply.png_base64) == SUN_PNG


def test_gives_the_search_history(handler: WorldRequestHandler) -> None:
    reply = handler.handle(GetSearchHistoryRequest(request_id="r5"))

    assert isinstance(reply, SearchHistoryReply)
    assert [(entry.searched_at, entry.query) for entry in reply.searches] == [
        ("2026-11-23T10:15", "fases da lua")
    ]


def test_a_missing_drawing_fails_as_not_found(handler: WorldRequestHandler) -> None:
    reply = handler.handle(GetDrawingRequest(request_id="r6", id="2026-11-23-lua.png"))

    assert reply == RequestFailedReply(request_id="r6", reason="not_found")


def test_an_unreadable_note_fails_as_unreadable(
    handler: WorldRequestHandler, discoveries_dir: Path
) -> None:
    (discoveries_dir / "2026-11-23-quebrada.md").write_bytes(b"\xff\xfe\xfa")
    request = GetDiscoveryRequest(
        request_id="r7", folder="discoveries", id="2026-11-23-quebrada.md"
    )

    assert handler.handle(request) == RequestFailedReply(request_id="r7", reason="unreadable")
