import logging
from collections.abc import Sequence
from typing import Protocol

from src.application.category_matcher import CategoryCandidate
from src.domain.discovery import Discovery
from src.domain.language_model import ChatMessage, Role, StructuredLanguageModel

logger = logging.getLogger(__name__)

NONE_OF_THEM = "nenhuma"
DEFAULT_CANDIDATE_COUNT = 5
CANDIDATES_PLACEHOLDER = "{candidates}"


class CandidateFinder(Protocol):
    def candidates(self, text: str, count: int) -> tuple[CategoryCandidate, ...]: ...


class DoodleCategoryChooser:
    """Chooses what to sketch for a discovery with retrieve and rerank.

    Retrieve: the embeddings bring the few categories closest to the discovery (fast, but
    they only compare wording, so "cachorro-quente" looks close to "cachorros"). Rerank: the
    language model reads the discovery and picks one of them, or none when nothing in the
    discovery is drawable. Its answer is data, not trust: anything outside the offered
    options is refused.
    """

    def __init__(
        self,
        candidate_finder: CandidateFinder,
        language_model: StructuredLanguageModel,
        instructions_template: str,
        candidate_count: int = DEFAULT_CANDIDATE_COUNT,
    ) -> None:
        self._candidate_finder = candidate_finder
        self._language_model = language_model
        self._instructions_template = instructions_template
        self._candidate_count = candidate_count

    def choose(self, discovery: Discovery) -> str | None:
        """The category to sketch, or None when none of the candidates fits.

        Raises EmbeddingError or LanguageModelError when a model cannot be reached.
        """
        candidates = self._candidate_finder.candidates(
            f"{discovery.title}. {discovery.summary}", self._candidate_count
        )
        options = [candidate.category for candidate in candidates]
        reply = self._language_model.complete_json(
            self._messages(discovery, candidates), choice_schema(options)
        )
        choice = reply.data.get("category")
        logger.info(
            "Doodle candidates for '%s': %s; chose %s",
            discovery.title,
            _describe(candidates),
            repr(choice),
        )
        if choice not in options:
            if choice != NONE_OF_THEM:
                logger.warning("Ignoring a doodle choice outside the options: %r", choice)
            return None
        return str(choice)

    def _messages(
        self, discovery: Discovery, candidates: Sequence[CategoryCandidate]
    ) -> list[ChatMessage]:
        option_list = "\n".join(
            f"- {candidate.category}: {candidate.label}" for candidate in candidates
        )
        saved_discovery = f"Título: {discovery.title}\nResumo: {discovery.summary}"
        return [
            ChatMessage(
                Role.SYSTEM,
                self._instructions_template.replace(CANDIDATES_PLACEHOLDER, option_list),
            ),
            ChatMessage(Role.USER, saved_discovery),
        ]


def choice_schema(options: Sequence[str]) -> dict[str, object]:
    """Only one of the options or "nenhuma" can be generated (Ollama's structured output)."""
    return {
        "type": "object",
        "properties": {"category": {"type": "string", "enum": [*options, NONE_OF_THEM]}},
        "required": ["category"],
    }


def _describe(candidates: Sequence[CategoryCandidate]) -> str:
    return ", ".join(f"{candidate.category} {candidate.similarity:.3f}" for candidate in candidates)
