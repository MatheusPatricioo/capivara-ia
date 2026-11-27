"""Answers what a visual client asks about the capybara's saved things.

It turns each request into exactly one reply: the expected one, or a RequestFailedReply,
so the client never waits for an answer that will not come.
"""

import base64
import logging
from typing import assert_never

from src.domain.search_log import SearchLogError, SearchRecord
from src.infrastructure.jsonl_search_log import JsonlSearchLog
from src.infrastructure.saved_files_reader import (
    SavedFile,
    SavedFileNotFoundError,
    SavedFilesReader,
    SavedFileUnreadableError,
)
from src.infrastructure.world_messages import WORLD_DATE_FORMAT
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
    WorldReply,
    WorldRequest,
)

logger = logging.getLogger(__name__)


class WorldRequestHandler:
    def __init__(self, saved_files: SavedFilesReader, search_log: JsonlSearchLog) -> None:
        self._saved_files = saved_files
        self._search_log = search_log

    def handle(self, request: WorldRequest) -> WorldReply:
        try:
            return self._answer(request)
        except SavedFileNotFoundError:
            return RequestFailedReply(request_id=request.request_id, reason="not_found")
        except (SavedFileUnreadableError, SearchLogError):
            logger.exception("Could not answer the request %s", request.type)
            return RequestFailedReply(request_id=request.request_id, reason="unreadable")

    def _answer(self, request: WorldRequest) -> WorldReply:
        match request:
            case ListDiscoveriesRequest():
                return DiscoveryListReply(
                    request_id=request.request_id,
                    folder=request.folder,
                    folder_path=self._saved_files.folder_path(request.folder).as_posix(),
                    discoveries=_summaries(self._saved_files.notes(request.folder)),
                )
            case GetDiscoveryRequest():
                return self._discovery(request)
            case ListDrawingsRequest():
                return DrawingListReply(
                    request_id=request.request_id,
                    folder_path=self._saved_files.folder_path("discoveries").as_posix(),
                    drawings=_summaries(self._saved_files.drawings()),
                )
            case GetDrawingRequest():
                return self._drawing(request)
            case GetSearchHistoryRequest():
                return SearchHistoryReply(
                    request_id=request.request_id,
                    searches=[_search_entry(record) for record in self._search_log.newest_first()],
                )
            case _:
                assert_never(request)

    def _discovery(self, request: GetDiscoveryRequest) -> DiscoveryReply:
        markdown = self._saved_files.note_text(request.folder, request.id)
        return DiscoveryReply(
            request_id=request.request_id,
            folder=request.folder,
            id=request.id,
            # The same title the list showed, so a note never changes name when opened.
            title=self._saved_files.note(request.folder, request.id).title,
            markdown=markdown,
        )

    def _drawing(self, request: GetDrawingRequest) -> DrawingReply:
        png = self._saved_files.drawing_png(request.id)
        return DrawingReply(
            request_id=request.request_id,
            id=request.id,
            title=self._saved_files.drawing(request.id).title,
            png_base64=base64.b64encode(png).decode("ascii"),
        )


def _summaries(saved_files: list[SavedFile]) -> list[SavedItemSummary]:
    return [
        SavedItemSummary(
            id=saved_file.file_name,
            title=saved_file.title,
            saved_at=saved_file.saved_at.strftime(WORLD_DATE_FORMAT),
            done=saved_file.done,
        )
        for saved_file in saved_files
    ]


def _search_entry(record: SearchRecord) -> SearchEntry:
    return SearchEntry(
        searched_at=record.searched_at.strftime(WORLD_DATE_FORMAT),
        query=record.query,
        pages=[FoundPage(title=page.title, url=page.url) for page in record.results],
    )
