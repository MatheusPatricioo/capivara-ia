import logging

from pydantic import Field

from src.application.tools.tool_arguments import (
    NonEmptyText,
    ToolArguments,
    parse_arguments,
    tool_parameters,
)
from src.domain.discovery_memory import DiscoveryMemory, DiscoveryMemoryError, RememberedDiscovery
from src.domain.language_model import ToolDefinition
from src.domain.tool import ToolError

DEFAULT_RESULT_COUNT = 3
NOTHING_REMEMBERED_MESSAGE = (
    "Nothing in your treasure is about that yet: it is new to you, so it is worth researching."
)

logger = logging.getLogger(__name__)


class RecallMemoryArguments(ToolArguments):
    query: NonEmptyText = Field(
        description="What you want to remember, in Brazilian Portuguese, e.g. 'vaga-lumes'."
    )


class RecallMemoryTool:
    """Agentic RAG: she decides when to search her own memory, like she decides to search the web.

    The automatic RAG (RelatedDiscoveries) only looks for what she noticed in the world.
    With this tool she can also check her treasure before researching any subject, and
    build on what she knows instead of saving the same discovery twice.
    """

    def __init__(
        self,
        memory: DiscoveryMemory,
        min_similarity: float,
        result_count: int = DEFAULT_RESULT_COUNT,
    ) -> None:
        self._memory = memory
        self._min_similarity = min_similarity
        self._result_count = result_count

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="recall_memory",
            description=(
                "Searches your treasure (the discoveries you already saved) by meaning and "
                "by words, and returns the closest ones with their summaries. Use it before "
                "researching a subject, to know what you already learned about it."
            ),
            parameters=tool_parameters(RecallMemoryArguments),
        )

    def run(self, arguments: dict[str, object]) -> str:
        query = parse_arguments(RecallMemoryArguments, arguments).query
        try:
            remembered = self._memory.recall(query, limit=self._result_count)
        except DiscoveryMemoryError as error:
            raise ToolError(f"your memory is not available right now: {error}") from error
        related = [
            remembered_discovery
            for remembered_discovery in remembered
            if remembered_discovery.similarity >= self._min_similarity
        ]
        logger.info("recall_memory '%s' brought back %d discovery(ies)", query, len(related))
        if not related:
            return NOTHING_REMEMBERED_MESSAGE
        return "\n\n".join(
            _format(position, remembered_discovery)
            for position, remembered_discovery in enumerate(related, start=1)
        )


def _format(position: int, remembered_discovery: RememberedDiscovery) -> str:
    discovery = remembered_discovery.discovery
    summary = " ".join(discovery.summary.split())
    return f"{position}. {discovery.title} (tema: {discovery.topic})\n{summary}"
