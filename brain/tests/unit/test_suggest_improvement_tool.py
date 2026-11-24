import logging
from collections.abc import Sequence
from datetime import date

import pytest

from src.application.repeated_suggestions import RepeatedSuggestions
from src.application.tools.conversation_discoveries import ConversationDiscoveries
from src.application.tools.suggest_improvement_tool import SuggestImprovementTool
from src.domain.discovery import Discovery
from src.domain.text_embedding import Embedding, EmbeddingError
from src.domain.tool import ToolError
from src.domain.world_suggestion import SavedSuggestion, SuggestionStorageError, WorldSuggestion
from tests.fakes.in_memory_discovery_memory import WordCountEmbedder
from tests.fakes.in_memory_suggestions import a_suggestion

TODAY = date(2026, 11, 24)
SAVED_FILE_NAME = "2026-11-24-vaga-lumes-no-jardim.md"
MIN_SIMILARITY = 0.80
VOCABULARY = ["laguinho", "vitórias-régias", "vaga-lumes", "jardim", "luneta"]
SUGGEST_TOOL_LOGGER = "src.application.tools.suggest_improvement_tool"
DISCOVERY = Discovery(
    title="Vaga-lumes",
    topic="insetos",
    summary="Eles piscam para conversar!",
    sources=("https://example.com/fireflies",),
    discovered_on=TODAY,
)
VALID_ARGUMENTS: dict[str, object] = {
    "request": "  Vaga-lumes no jardim  ",
    "reason": "Aprendi que eles piscam para conversar, e eu queria ver isso à noite.",
}


class InMemorySuggestionRepository:
    """Saves into a list and reads earlier plus new suggestions back, like the folder."""

    def __init__(self, earlier_requests: Sequence[str] = ()) -> None:
        self._earlier = [a_suggestion(request) for request in earlier_requests]
        self.new_suggestions: list[WorldSuggestion] = []

    def save(self, suggestion: WorldSuggestion) -> str:
        self.new_suggestions.append(suggestion)
        return SAVED_FILE_NAME

    def saved_suggestions(self) -> list[SavedSuggestion]:
        return [
            SavedSuggestion(f"suggestion-{position}.md", suggestion)
            for position, suggestion in enumerate(self._earlier + self.new_suggestions)
        ]


class FullDiskSuggestionRepository(InMemorySuggestionRepository):
    def save(self, suggestion: WorldSuggestion) -> str:
        raise SuggestionStorageError("no space left on device")


class OfflineEmbedder:
    def embed(self, texts: Sequence[str]) -> list[Embedding]:
        raise EmbeddingError("Ollama is not running")


def build_tool(
    repository: InMemorySuggestionRepository,
    saved_discoveries: ConversationDiscoveries,
    embedder: WordCountEmbedder | OfflineEmbedder,
) -> SuggestImprovementTool:
    return SuggestImprovementTool(
        repository,
        RepeatedSuggestions(repository, embedder, MIN_SIMILARITY),
        saved_discoveries,
        today=lambda: TODAY,
    )


@pytest.fixture
def repository() -> InMemorySuggestionRepository:
    return InMemorySuggestionRepository(earlier_requests=["Um laguinho com vitórias-régias"])


@pytest.fixture
def saved_discoveries() -> ConversationDiscoveries:
    """She already saved a discovery in this conversation."""
    discoveries = ConversationDiscoveries()
    discoveries.remember(DISCOVERY)
    return discoveries


@pytest.fixture
def tool(
    repository: InMemorySuggestionRepository, saved_discoveries: ConversationDiscoveries
) -> SuggestImprovementTool:
    return build_tool(repository, saved_discoveries, WordCountEmbedder(VOCABULARY))


def test_definition_is_named_suggest_improvement(tool: SuggestImprovementTool) -> None:
    assert tool.definition.name == "suggest_improvement"


def test_definition_does_not_let_the_model_name_the_inspiration(
    tool: SuggestImprovementTool,
) -> None:
    assert tool.definition.parameters["required"] == ["request", "reason"]


def test_saves_the_suggestion_with_the_request_and_reason_trimmed(
    tool: SuggestImprovementTool, repository: InMemorySuggestionRepository
) -> None:
    tool.run(VALID_ARGUMENTS)

    assert repository.new_suggestions == [
        WorldSuggestion(
            request="Vaga-lumes no jardim",
            reason="Aprendi que eles piscam para conversar, e eu queria ver isso à noite.",
            inspired_by="Vaga-lumes",
            suggested_on=TODAY,
        )
    ]


def test_takes_the_latest_discovery_of_the_conversation_as_the_inspiration(
    tool: SuggestImprovementTool,
    repository: InMemorySuggestionRepository,
    saved_discoveries: ConversationDiscoveries,
) -> None:
    saved_discoveries.remember(
        Discovery("Jardins noturnos", "plantas", "Flores que abrem à noite.", (), TODAY)
    )

    tool.run(VALID_ARGUMENTS)

    assert repository.new_suggestions[0].inspired_by == "Jardins noturnos"


def test_tells_the_model_the_suggestion_is_not_in_the_world_yet(
    tool: SuggestImprovementTool,
) -> None:
    result = tool.run(VALID_ARGUMENTS)

    assert result == (
        f"Suggestion saved as {SAVED_FILE_NAME}. Matheus reads your suggestions and may "
        "build this one someday: it is not in your world yet."
    )


def test_refuses_a_suggestion_before_any_discovery_was_saved(
    repository: InMemorySuggestionRepository,
) -> None:
    tool = build_tool(repository, ConversationDiscoveries(), WordCountEmbedder(VOCABULARY))

    with pytest.raises(ToolError, match="save a discovery with save_discovery first"):
        tool.run(VALID_ARGUMENTS)


def test_refuses_a_second_suggestion_in_the_same_cycle(tool: SuggestImprovementTool) -> None:
    tool.run(VALID_ARGUMENTS)

    with pytest.raises(ToolError, match="already made a suggestion in this cycle"):
        tool.run({"request": "Uma luneta", "reason": "Para ver estrelas."})


def test_refuses_a_repeat_of_an_earlier_suggestion_naming_it(
    tool: SuggestImprovementTool,
) -> None:
    with pytest.raises(ToolError, match="'Um laguinho com vitórias-régias'"):
        tool.run({"request": "Vitórias-régias no laguinho", "reason": "São enormes!"})


def test_a_refused_repeat_still_allows_a_new_suggestion_in_the_cycle(
    tool: SuggestImprovementTool, repository: InMemorySuggestionRepository
) -> None:
    with pytest.raises(ToolError):
        tool.run({"request": "Vitórias-régias no laguinho", "reason": "São enormes!"})

    tool.run(VALID_ARGUMENTS)

    assert [saved.request for saved in repository.new_suggestions] == ["Vaga-lumes no jardim"]


def test_saves_anyway_when_repeats_cannot_be_checked(
    repository: InMemorySuggestionRepository, saved_discoveries: ConversationDiscoveries
) -> None:
    tool = build_tool(repository, saved_discoveries, OfflineEmbedder())

    tool.run(VALID_ARGUMENTS)

    assert len(repository.new_suggestions) == 1


def test_logs_a_warning_when_repeats_cannot_be_checked(
    repository: InMemorySuggestionRepository,
    saved_discoveries: ConversationDiscoveries,
    caplog: pytest.LogCaptureFixture,
) -> None:
    tool = build_tool(repository, saved_discoveries, OfflineEmbedder())

    with caplog.at_level(logging.WARNING, logger=SUGGEST_TOOL_LOGGER):
        tool.run(VALID_ARGUMENTS)

    assert "Could not check for repeated suggestions" in caplog.text


def test_refuses_a_blank_request(tool: SuggestImprovementTool) -> None:
    with pytest.raises(ToolError, match="needs a request"):
        tool.run({"request": "  ", "reason": "Porque sim."})


def test_refuses_a_missing_reason(tool: SuggestImprovementTool) -> None:
    with pytest.raises(ToolError, match="needs a reason"):
        tool.run({"request": "Vaga-lumes no jardim"})


def test_refuses_a_request_that_is_not_text(tool: SuggestImprovementTool) -> None:
    with pytest.raises(ToolError, match="needs a request"):
        tool.run({"request": 42, "reason": "Porque sim."})


def test_reports_a_storage_failure_to_the_model(
    saved_discoveries: ConversationDiscoveries,
) -> None:
    tool = build_tool(
        FullDiskSuggestionRepository(), saved_discoveries, WordCountEmbedder(VOCABULARY)
    )

    with pytest.raises(ToolError, match="could not save the suggestion: no space left"):
        tool.run(VALID_ARGUMENTS)


def test_a_failed_save_still_allows_another_try_in_the_cycle(
    saved_discoveries: ConversationDiscoveries,
) -> None:
    repository = FullDiskSuggestionRepository()
    tool = build_tool(repository, saved_discoveries, WordCountEmbedder(VOCABULARY))
    with pytest.raises(ToolError):
        tool.run(VALID_ARGUMENTS)

    with pytest.raises(ToolError, match="could not save"):
        tool.run(VALID_ARGUMENTS)
