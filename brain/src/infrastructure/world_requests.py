"""Requests a visual client sends to read what the capybara saved, and the brain's replies.

Unlike events, a request expects an answer: the client picks a request_id, and the reply
carries the same id back, so the client knows which question it answers even when replies
arrive out of order. Only the client that asked gets the reply.

The client never touches the discoveries folder: it asks for items by an opaque id and
receives titles already made by the brain, so file naming rules stay on this side.
"""

import json
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field, StringConstraints, TypeAdapter, ValidationError

MAX_REQUEST_ID_LENGTH = 64
MAX_ITEM_ID_LENGTH = 120

RequestId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=MAX_REQUEST_ID_LENGTH, pattern=r"^[A-Za-z0-9_-]+$"),
]
ItemId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=MAX_ITEM_ID_LENGTH,
        # One name and one extension: no slashes, no "..", so it never leaves the folder.
        pattern=r"^[A-Za-z0-9_-]+\.[a-z]+$",
    ),
]
DiscoveryFolder = Literal["discoveries", "suggestions"]
"""Which notes: her discoveries, or the improvements she suggested to her creator."""


class ListDiscoveriesRequest(BaseModel):
    type: Literal["list_discoveries"] = "list_discoveries"
    request_id: RequestId
    folder: DiscoveryFolder


class GetDiscoveryRequest(BaseModel):
    type: Literal["get_discovery"] = "get_discovery"
    request_id: RequestId
    folder: DiscoveryFolder
    id: ItemId


class ListDrawingsRequest(BaseModel):
    type: Literal["list_drawings"] = "list_drawings"
    request_id: RequestId


class GetDrawingRequest(BaseModel):
    type: Literal["get_drawing"] = "get_drawing"
    request_id: RequestId
    id: ItemId


class GetSearchHistoryRequest(BaseModel):
    type: Literal["get_search_history"] = "get_search_history"
    request_id: RequestId


WorldRequest = (
    ListDiscoveriesRequest
    | GetDiscoveryRequest
    | ListDrawingsRequest
    | GetDrawingRequest
    | GetSearchHistoryRequest
)


class SavedItemSummary(BaseModel):
    """One note or drawing in a list: enough to show it and to ask for it later."""

    id: ItemId
    title: str
    """Ready to show, like "gato dormindo"."""
    saved_at: str
    """Local date and time, like "2026-11-25T14:30"."""
    done: bool = False
    """True for a suggestion her creator already built; always False for anything else."""


class DiscoveryListReply(BaseModel):
    """The notes of one folder, the newest first."""

    type: Literal["discovery_list"] = "discovery_list"
    request_id: RequestId
    folder: DiscoveryFolder
    folder_path: str
    """Where the notes are on the brain's machine, only to show or open it there."""
    discoveries: list[SavedItemSummary]


class DiscoveryReply(BaseModel):
    type: Literal["discovery"] = "discovery"
    request_id: RequestId
    folder: DiscoveryFolder
    id: ItemId
    title: str
    markdown: str


class DrawingListReply(BaseModel):
    """Her drawings, the newest first, without the images: each one is asked for apart,
    so no message grows with the size of the gallery."""

    type: Literal["drawing_list"] = "drawing_list"
    request_id: RequestId
    folder_path: str
    drawings: list[SavedItemSummary]


class DrawingReply(BaseModel):
    """One drawing as a PNG file in base64, because JSON only carries text."""

    type: Literal["drawing"] = "drawing"
    request_id: RequestId
    id: ItemId
    title: str
    png_base64: str = Field(min_length=1)


class FoundPage(BaseModel):
    title: str
    url: str


class SearchEntry(BaseModel):
    searched_at: str
    query: str
    pages: list[FoundPage]


class SearchHistoryReply(BaseModel):
    """Every web search she did, the newest first."""

    type: Literal["search_history"] = "search_history"
    request_id: RequestId
    searches: list[SearchEntry]


FailureReason = Literal["not_found", "unreadable", "invalid_request"]


class RequestFailedReply(BaseModel):
    """Sent instead of the expected reply, so the client stops waiting at once."""

    type: Literal["request_failed"] = "request_failed"
    request_id: RequestId
    reason: FailureReason


WorldReply = (
    DiscoveryListReply
    | DiscoveryReply
    | DrawingListReply
    | DrawingReply
    | SearchHistoryReply
    | RequestFailedReply
)

REQUEST_TYPES = frozenset(
    request_model.model_fields["type"].default for request_model in get_args(WorldRequest)
)

_WORLD_REQUEST_ADAPTER: TypeAdapter[WorldRequest] = TypeAdapter(
    Annotated[WorldRequest, Field(discriminator="type")]
)
_WORLD_REPLY_ADAPTER: TypeAdapter[WorldReply] = TypeAdapter(
    Annotated[WorldReply, Field(discriminator="type")]
)


def parse_world_request(payload: str | bytes) -> WorldRequest | None:
    """Returns the request, or None when the payload is not a valid request."""
    try:
        return _WORLD_REQUEST_ADAPTER.validate_json(payload)
    except ValidationError:
        return None


def invalid_request_reply(payload: str | bytes) -> RequestFailedReply | None:
    """For a request that names a known type and a valid request_id but is broken otherwise
    (like an id with ".."): a failure the client can match, instead of a silent drop.
    None when the payload does not even look like a request."""
    try:
        fields = json.loads(payload)
    except ValueError:
        return None
    if not isinstance(fields, dict) or fields.get("type") not in REQUEST_TYPES:
        return None
    try:
        return RequestFailedReply.model_validate(
            {"request_id": fields.get("request_id"), "reason": "invalid_request"}
        )
    except ValidationError:
        return None


def parse_world_reply(payload: str | bytes) -> WorldReply | None:
    """Returns the reply, or None when the payload is not a valid reply.

    The brain only sends replies; this is how any client (and the tests) reads them.
    """
    try:
        return _WORLD_REPLY_ADAPTER.validate_json(payload)
    except ValidationError:
        return None
