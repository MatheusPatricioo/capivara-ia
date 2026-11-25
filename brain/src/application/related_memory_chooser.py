import logging
from collections.abc import Sequence

from src.domain.discovery import Discovery
from src.domain.discovery_memory import RememberedDiscovery
from src.domain.language_model import ChatMessage, Role, StructuredLanguageModel

NONE_OF_THEM = "nenhuma"
CANDIDATES_PLACEHOLDER = "{candidates}"

logger = logging.getLogger(__name__)


class RelatedMemoryChooser:
    """The rerank step of the long-term memory: is any candidate really about the subject?

    The search (retrieve) is fast but only compares wording and meaning roughly: "um sapo
    na beira do lago" comes close to a discovery about mushrooms because both mention water.
    A fixed similarity threshold could not separate those cases (the evals measured 47% of
    right decisions at 0.70). Here the language model reads the subject and the few closest
    discoveries and picks the one that is really about it, or none.

    Like the doodle choice, the answer can only be one of the offered numbers or "nenhuma"
    (structured output), and anything else is refused in code.
    """

    def __init__(self, language_model: StructuredLanguageModel, instructions_template: str) -> None:
        self._language_model = language_model
        self._instructions_template = instructions_template

    def choose(self, subject: str, candidates: Sequence[RememberedDiscovery]) -> Discovery | None:
        """Raises LanguageModelError when the model cannot be reached."""
        if not candidates:
            return None
        options = [str(position) for position in range(1, len(candidates) + 1)]
        reply = self._language_model.complete_json(
            self._messages(subject, candidates), _choice_schema(options)
        )
        choice = reply.data.get("choice")
        logger.info(
            "Related memory for '%s': candidates %s; chose %r",
            subject,
            ", ".join(f"'{item.discovery.title}' {item.similarity:.3f}" for item in candidates),
            choice,
        )
        if choice not in options:
            if choice != NONE_OF_THEM:
                logger.warning("Ignoring a memory choice outside the options: %r", choice)
            return None
        return candidates[options.index(str(choice))].discovery

    def _messages(
        self, subject: str, candidates: Sequence[RememberedDiscovery]
    ) -> list[ChatMessage]:
        option_list = "\n".join(
            f"{position}: {item.discovery.title} — {_one_line(item.discovery.summary)}"
            for position, item in enumerate(candidates, start=1)
        )
        return [
            ChatMessage(
                Role.SYSTEM,
                self._instructions_template.replace(CANDIDATES_PLACEHOLDER, option_list),
            ),
            ChatMessage(Role.USER, f"Ela reparou em: {subject}"),
        ]


def _choice_schema(options: Sequence[str]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"choice": {"type": "string", "enum": [*options, NONE_OF_THEM]}},
        "required": ["choice"],
    }


def _one_line(text: str) -> str:
    return " ".join(text.split())
