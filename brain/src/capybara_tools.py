"""Builds the capybara's tools. Shared by the chat and by the autonomous (live) mode."""

from ddgs import DDGS

from src.application.tools.draw_tool import DrawTool
from src.application.tools.embodied_tool import EmbodiedTool
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.saved_discoveries import SavedDiscoveries
from src.application.tools.seen_sources import SeenSources
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.body import Body, Place
from src.domain.chalkboard import Chalkboard
from src.domain.tool import Tool
from src.infrastructure.duckduckgo_web_searcher import DuckDuckGoWebSearcher
from src.infrastructure.json_search_history import JsonSearchHistory
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.png_drawing_repository import PngDrawingRepository
from src.infrastructure.settings import Settings

SEARCH_HISTORY_FILE_NAME = "search-history.json"
# Tools whose results skip the general reminder. After save_discovery, the reminder ("call
# save_discovery now... then tell Matheus") buried the invitation to draw and made her narrate
# instead of drawing. Measured on real moments after a save: 11/20 drawings with it, 16/20 without.
TOOL_RESULT_REMINDER_OVERRIDES = {"save_discovery": ""}


def build_capybara_tools(
    settings: Settings, chalkboard: Chalkboard, body: Body | None = None
) -> list[Tool]:
    """Creates fresh tools for one conversation. With a body, each tool walks to its place."""
    seen_sources = SeenSources()
    saved_discoveries = SavedDiscoveries()
    web_search_tool = WebSearchTool(
        DuckDuckGoWebSearcher(DDGS(), backend=settings.web_search_backend),
        seen_sources=seen_sources,
        search_history=JsonSearchHistory(settings.discoveries_dir / SEARCH_HISTORY_FILE_NAME),
    )
    save_discovery_tool = SaveDiscoveryTool(
        MarkdownDiscoveryRepository(settings.discoveries_dir),
        seen_sources,
        saved_discoveries=saved_discoveries,
    )
    draw_tool = DrawTool(
        PngDrawingRepository(settings.discoveries_dir),
        chalkboard,
        saved_discoveries,
        body=body,
    )
    if body is None:
        return [web_search_tool, save_discovery_tool, draw_tool]
    return [
        EmbodiedTool(web_search_tool, body, Place.COMPUTER),
        EmbodiedTool(save_discovery_tool, body, Place.MURAL),
        EmbodiedTool(draw_tool, body, Place.CHALKBOARD),
    ]
