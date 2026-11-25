"""Builds the capybara's tools. Shared by the chat and by the autonomous (live) mode."""

import httpx
from ddgs import DDGS

from src.application.category_matcher import CategoryMatcher
from src.application.chalkboard_artist import ChalkboardArtist
from src.application.doodle_category_chooser import DoodleCategoryChooser
from src.application.illustrate_discovery import IllustrateDiscovery
from src.application.remembering_discovery_repository import RememberingDiscoveryRepository
from src.application.repeated_suggestions import RepeatedSuggestions
from src.application.tools.conversation_discoveries import ConversationDiscoveries
from src.application.tools.embodied_tool import EmbodiedTool
from src.application.tools.feeling_tool import Feeler, FeelingTool, always, search_feeling
from src.application.tools.recall_memory_tool import RecallMemoryTool
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.seen_sources import SeenSources
from src.application.tools.suggest_improvement_tool import SuggestImprovementTool
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.body import Body, Place
from src.domain.capybara_hand import CapybaraHand
from src.domain.chalkboard import Chalkboard
from src.domain.discovery import DiscoveryRepository
from src.domain.discovery_memory import DiscoveryMemory
from src.domain.feelings.appraisal import EventKind
from src.domain.language_model import StructuredLanguageModel
from src.domain.tool import Tool
from src.infrastructure.duckduckgo_web_searcher import DuckDuckGoWebSearcher
from src.infrastructure.json_embedding_cache import JsonEmbeddingCache
from src.infrastructure.json_search_history import JsonSearchHistory
from src.infrastructure.jsonl_search_log import JsonlSearchLog
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.ollama_text_embedder import OllamaTextEmbedder
from src.infrastructure.png_drawing_repository import PngDrawingRepository
from src.infrastructure.prompt_loader import load_prompt
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
CHOOSE_DOODLE_PROMPT_NAME = "choose_doodle"
# Added to every successful save: the moment a discovery can turn into a wish for her world.
# Measured on real moments right after a save: 0/20 suggestions with the rule only in the
# system prompt, about 1 in 10 with this invitation (all concrete and in the right moments).
SUGGESTION_INVITATION_PROMPT_NAME = "suggestion_invitation"


def build_capybara_tools(
    settings: Settings,
    chalkboard: Chalkboard,
    language_model: StructuredLanguageModel,
    http_client: httpx.Client,
    body: Body | None = None,
    memory: DiscoveryMemory | None = None,
    heart: Feeler | None = None,
) -> list[Tool]:
    """Creates fresh tools for one conversation. With a body, each tool walks to its place.

    The doodle for a discovery is chosen with retrieve and rerank: http_client reaches
    Ollama's embedding model (retrieve) and language_model picks among them (rerank).

    With a memory, every saved discovery is also remembered for later cycles, and she can
    search her treasure with recall_memory (agentic RAG).

    After saving a discovery, she may suggest one thing for her world (suggest_improvement),
    inspired by the discovery she just saved in this same conversation.

    With a heart, she feels what comes out of her tools: a search that found something,
    one that found nothing, a saved discovery, a wish made.

    There is no draw tool: every saved discovery is offered a drawing automatically, because
    with a draw tool she often said she would draw and never called it.
    """
    seen_sources = SeenSources()
    saved_discoveries = ConversationDiscoveries()
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
        DoodleCategoryChooser(
            _build_category_matcher(settings, http_client),
            language_model,
            load_prompt(CHOOSE_DOODLE_PROMPT_NAME),
        ),
        load_doodle_library(),
        CapybaraHand(),
        ChalkboardArtist(PngDrawingRepository(settings.discoveries_dir), chalkboard, body=body),
    )
    save_discovery_tool = SaveDiscoveryTool(
        _build_discovery_repository(settings, memory),
        seen_sources,
        illustrate=illustrator.illustrate,
        saved_discoveries=saved_discoveries,
        follow_up=load_prompt(SUGGESTION_INVITATION_PROMPT_NAME),
    )
    suggest_improvement_tool = _build_suggest_improvement_tool(
        settings, http_client, saved_discoveries
    )
    tools: list[Tool] = [web_search_tool, save_discovery_tool, suggest_improvement_tool]
    if heart is not None:
        tools = [
            FeelingTool(web_search_tool, heart, search_feeling, EventKind.SEARCH_FAILED),
            FeelingTool(save_discovery_tool, heart, always(EventKind.DISCOVERY_SAVED)),
            FeelingTool(suggest_improvement_tool, heart, always(EventKind.WISH_MADE)),
        ]
    if memory is not None and settings.memory_recall_tool:
        # Agentic RAG: she decides when to look into her treasure, like a web search.
        tools.append(RecallMemoryTool(memory, settings.memory_recall_min_similarity))
    if body is None:
        return tools
    # Searching, saving and remembering all happen at the computer, where her files live.
    return [EmbodiedTool(tool, body, Place.COMPUTER) for tool in tools]


def _build_suggest_improvement_tool(
    settings: Settings, http_client: httpx.Client, saved_discoveries: ConversationDiscoveries
) -> SuggestImprovementTool:
    suggestions = MarkdownSuggestionRepository(settings.discoveries_dir)
    return SuggestImprovementTool(
        suggestions,
        RepeatedSuggestions(
            suggestions,
            OllamaTextEmbedder(http_client, settings.ollama_embedding_model),
            settings.suggestion_repeat_min_similarity,
        ),
        saved_discoveries,
    )


def _build_discovery_repository(
    settings: Settings, memory: DiscoveryMemory | None
) -> DiscoveryRepository:
    repository = MarkdownDiscoveryRepository(settings.discoveries_dir)
    if memory is None:
        return repository
    return RememberingDiscoveryRepository(repository, memory)


def _build_category_matcher(settings: Settings, http_client: httpx.Client) -> CategoryMatcher:
    model = settings.ollama_embedding_model
    return CategoryMatcher(
        OllamaTextEmbedder(http_client, model),
        load_category_labels(),
        JsonEmbeddingCache(DEFAULT_EMBEDDING_CACHE_FILE, model),
    )
