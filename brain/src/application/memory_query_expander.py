import logging

from src.domain.language_model import ChatMessage, Role, StructuredLanguageModel

QUERY_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"query": {"type": "string"}},
    "required": ["query"],
}

logger = logging.getLogger(__name__)


class MemoryQueryExpander:
    """Query rewriting: turns what she saw into a search with the subject's real names.

    "luzinhas piscando no jardim à noite" shares no word with a discovery about
    "vaga-lumes", so full-text search finds nothing and the embedding is only lukewarm.
    Rewritten as "vaga-lumes insetos bioluminescência luz", both searches find it.
    The original description is kept in the search too, so a bad rewrite cannot lose it.
    """

    def __init__(self, language_model: StructuredLanguageModel, instructions: str) -> None:
        self._language_model = language_model
        self._instructions = instructions

    def expand(self, subject: str) -> str:
        """The subject followed by its rewrite. Raises LanguageModelError when unreachable."""
        reply = self._language_model.complete_json(
            [
                ChatMessage(Role.SYSTEM, self._instructions),
                ChatMessage(Role.USER, subject),
            ],
            QUERY_SCHEMA,
        )
        rewrite = reply.data.get("query")
        if not isinstance(rewrite, str) or not rewrite.strip():
            logger.warning("Ignoring an empty query rewrite for '%s'", subject)
            return subject
        logger.info("Memory query for '%s' rewritten as '%s'", subject, rewrite.strip())
        return f"{subject} {rewrite.strip()}"
