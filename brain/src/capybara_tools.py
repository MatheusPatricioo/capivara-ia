"""Builds the capybara's tools. Shared by the chat and by the autonomous (live) mode."""

from ddgs import DDGS

from src.application.chalkboard_artist import ChalkboardArtist
from src.application.illustrate_discovery import IllustrateDiscovery
from src.application.tools.embodied_tool import EmbodiedTool
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.seen_sources import SeenSources
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.body import Body, Place
from src.domain.chalkboard import Chalkboard
from src.domain.language_model import StructuredLanguageModel
from src.domain.tool import Tool
from src.infrastructure.duckduckgo_web_searcher import DuckDuckGoWebSearcher
from src.infrastructure.json_search_history import JsonSearchHistory
from src.infrastructure.json_sketch_book import load_sketch_book
from src.infrastructure.jsonl_search_log import JsonlSearchLog
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.png_drawing_repository import PngDrawingRepository
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import Settings

SEARCH_HISTORY_FILE_NAME = "search-history.json"
# Every search with its results, one JSON per line; read by the computer screen in Godot.
SEARCH_LOG_RELATIVE_PATH = "history/searches.jsonl"
ILLUSTRATE_DISCOVERY_PROMPT_NAME = "illustrate_discovery"
# Tools whose results skip the general reminder. After save_discovery, the reminder ("call
# save_discovery now... then tell Matheus") buried what had just happened and made her narrate
# instead of acting. Measured on real moments after a save: 11/20 drawings with it, 16/20 without.
TOOL_RESULT_REMINDER_OVERRIDES = {"save_discovery": ""}


def build_capybara_tools(
    settings: Settings,
    chalkboard: Chalkboard,
    language_model: StructuredLanguageModel,
    body: Body | None = None,
) -> list[Tool]:
    """Creates fresh tools for one conversation. With a body, each tool walks to its place.

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
        language_model,
        ChalkboardArtist(PngDrawingRepository(settings.discoveries_dir), chalkboard, body=body),
        load_prompt(ILLUSTRATE_DISCOVERY_PROMPT_NAME),
        load_sketch_book(),
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
