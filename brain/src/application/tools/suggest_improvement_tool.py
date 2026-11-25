import logging
from collections.abc import Callable
from datetime import date

from pydantic import Field

from src.application.repeated_suggestions import RepeatedSuggestions
from src.application.tools.conversation_discoveries import ConversationDiscoveries
from src.application.tools.tool_arguments import (
    NonEmptyText,
    ToolArguments,
    parse_arguments,
    tool_parameters,
)
from src.domain.language_model import ToolDefinition
from src.domain.text_embedding import EmbeddingError
from src.domain.tool import ToolError
from src.domain.world_suggestion import (
    InvalidSuggestionError,
    SuggestionStorageError,
    WorldSuggestion,
    WorldSuggestionRepository,
)

logger = logging.getLogger(__name__)


class SuggestImprovementArguments(ToolArguments):
    request: NonEmptyText = Field(
        description=(
            "What you would like in your world, short like a title, "
            "e.g. 'Um laguinho com vitórias-régias'."
        )
    )
    reason: NonEmptyText = Field(description="Why you want it, tied to what you just learned.")


class SuggestImprovementTool:
    """Lets the capybara suggest something for her world, inspired by what she just learned.

    The rules live here, in code, not only in the prompt (a small model forgets prompts):
    - only after saving a discovery in this conversation, which becomes the inspiration;
    - at most one suggestion per conversation (one cycle of the live mode);
    - not a repeat, by meaning, of a suggestion she already made.
    A fresh tool is built for every conversation, so the limit starts over each cycle.
    """

    def __init__(
        self,
        repository: WorldSuggestionRepository,
        repeated_suggestions: RepeatedSuggestions,
        saved_discoveries: ConversationDiscoveries,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._repository = repository
        self._repeated_suggestions = repeated_suggestions
        self._saved_discoveries = saved_discoveries
        self._today = today
        self._has_suggested = False

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="suggest_improvement",
            description=(
                "Right after saving a discovery, suggests one concrete thing to add to your "
                "world because of what you learned (for example, after learning about "
                "fireflies: 'Vaga-lumes no jardim à noite'). Matheus reads your suggestions "
                "and may build them someday: suggesting does not change your world now. "
                "At most one per cycle. Written in Brazilian Portuguese."
            ),
            parameters=tool_parameters(SuggestImprovementArguments),
        )

    def run(self, arguments: dict[str, object]) -> str:
        self._ensure_first_suggestion_of_the_cycle()
        suggestion = self._build_suggestion(arguments)
        self._ensure_not_a_repeat(suggestion.request)
        try:
            file_name = self._repository.save(suggestion)
        except SuggestionStorageError as error:
            raise ToolError(f"could not save the suggestion: {error}") from error
        self._has_suggested = True
        logger.info("Suggestion saved: %s (inspired by '%s')", file_name, suggestion.inspired_by)
        return (
            f"Suggestion saved as {file_name}. Matheus reads your suggestions and may build "
            "this one someday: it is not in your world yet."
        )

    def _ensure_first_suggestion_of_the_cycle(self) -> None:
        if self._has_suggested:
            raise ToolError(
                "you already made a suggestion in this cycle: one is enough, "
                "keep the next idea for another day"
            )

    def _build_suggestion(self, arguments: dict[str, object]) -> WorldSuggestion:
        inspiration = self._saved_discoveries.latest
        if inspiration is None:
            raise ToolError(
                "suggestions come from what you just learned: save a discovery with "
                "save_discovery first, then suggest something inspired by it"
            )
        parsed = parse_arguments(SuggestImprovementArguments, arguments)
        try:
            return WorldSuggestion(
                request=parsed.request,
                reason=parsed.reason,
                inspired_by=inspiration.title,
                suggested_on=self._today(),
            )
        except InvalidSuggestionError as error:
            raise ToolError(f"invalid suggestion: {error}") from error

    def _ensure_not_a_repeat(self, request: str) -> None:
        """Without the embedding model the check is skipped: a repeat is better than no idea."""
        try:
            earlier = self._repeated_suggestions.earlier_version_of(request)
        except EmbeddingError as error:
            logger.warning("Could not check for repeated suggestions, saving anyway: %s", error)
            return
        if earlier is not None:
            raise ToolError(
                f"you already suggested something like this: '{earlier.request}'. "
                "Suggest something different, or nothing this time"
            )
