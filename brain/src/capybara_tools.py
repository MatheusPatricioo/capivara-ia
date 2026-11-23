"""Builds the capybara's tools. Shared by the chat and by the autonomous (live) mode."""

import httpx
from ddgs import DDGS

from src.application.category_matcher import CategoryMatcher
from src.application.chalkboard_artist import ChalkboardArtist
from src.application.illustrate_discovery import IllustrateDiscovery
from src.application.tools.embodied_tool import EmbodiedTool
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.seen_sources import SeenSources
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.body import Body, Place
from src.domain.chalkboard import Chalkboard
from src.domain.tool import Tool
from src.infrastructure.duckduckgo_web_searcher import DuckDuckGoWebSearcher
from src.infrastructure.json_embedding_cache import JsonEmbeddingCache
from src.infrastructure.json_search_history import JsonSearchHistory
from src.infrastructure.jsonl_search_log import JsonlSearchLog
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.ollama_text_embedder import OllamaTextEmbedder
from src.infrastructure.png_drawing_repository import PngDrawingRepository
from src.infrastructure.quickdraw_doodles import (
    DEFAULT_EMBEDDING_CACHE_FILE,
    load_category_labels,
    load_doodle_library,
)
from src.infrastructure.settings import Settings

SEARCH_HISTORY_FILE_NAME = "search-history.json"
# Every search with its results, one JSON per line; read by the computer screen in Godot.
SEARCH_LOG_RELATIVE_PATH = "history/searches.jsonl"
# Tools whose results skip the general reminder. After save_discovery, the reminder ("call
# save_discovery now... then tell Matheus") buried what had just happened and made her narrate
# instead of acting. Measured on real moments after a save: 11/20 drawings with it, 16/20 without.
TOOL_RESULT_REMINDER_OVERRIDES = {"save_discovery": ""}


def build_capybara_tools(
    settings: Settings,
    chalkboard: Chalkboard,
    http_client: httpx.Client,
    body: Body | None = None,
) -> list[Tool]:
    """Creates fresh tools for one conversation. With a body, each tool walks to its place.

    http_client talks to Ollama, whose embedding model picks the doodle for a discovery.

    There is no draw tool: every saved discovery is offered a drawing automatically, because
    with a draw tool she often said she would draw and never called it.
    """
    seen_sources = SeenSources()
    web_search_tool = WebSearchTool(
        DuckDuckGoWebSearcher(
            DDGS(),
            backend=settings.web_search_backend,
            region=settings.web_search_region,
        ),
        seen_sources=seen_sources,
        search_history=JsonSearchHistory(settings.discoveries_dir / SEARCH_HISTORY_FILE_NAME),
        search_log=JsonlSearchLog(settings.discoveries_dir / SEARCH_LOG_RELATIVE_PATH),
    )
    illustrator = IllustrateDiscovery(
        _build_category_matcher(settings, http_client),
        load_doodle_library(),
        ChalkboardArtist(PngDrawingRepository(settings.discoveries_dir), chalkboard, body=body),
        min_margin=settings.doodle_min_margin,
    )
    save_discovery_tool = SaveDiscoveryTool(
        MarkdownDiscoveryRepository(settings.discoveries_dir),
        seen_sources,
        illustrate=illustrator.illustrate,
    )
    if body is None:
        return [web_search_tool, save_discovery_tool]
    return [
        EmbodiedTool(web_search_tool, body, Place.COMPUTER),
        # Saving a discovery writes a file, and her files live in the computer.
        EmbodiedTool(save_discovery_tool, body, Place.COMPUTER),
    ]


def _build_category_matcher(settings: Settings, http_client: httpx.Client) -> CategoryMatcher:
    model = settings.ollama_embedding_model
    return CategoryMatcher(
        OllamaTextEmbedder(http_client, model),
        load_category_labels(),
        JsonEmbeddingCache(DEFAULT_EMBEDDING_CACHE_FILE, model),
    )
