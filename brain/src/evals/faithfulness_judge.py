"""LLM-as-judge: does her summary stick to the pages she read?

The judge does not give a free score. It breaks the summary into factual claims and, for
each one, has to quote the sentence of the pages that supports it (or leave the quote
empty). The code then checks that every quote really is in the pages and computes the
score itself. Asking for evidence instead of an opinion is what makes a small judge
usable: the first version, asked for a 1-5 score, flagged supported claims as invented.
"""

import re
import unicodedata
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from src.domain.discovery import Discovery
from src.domain.language_model import ChatMessage, Role, StructuredLanguageModel

# The claim comes before the quote on purpose: the model writes in order, so it states the
# claim first and then has to find where the pages say it.
VERDICT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "quote": {
                        "type": "string",
                        "description": "The exact words of the pages that support it, or ''.",
                    },
                },
                "required": ["claim", "quote"],
            },
        },
    },
    "required": ["claims"],
}
MIN_QUOTE_WORDS = 3
NON_WORD = re.compile(r"[^a-z0-9]+")


class JudgeError(Exception):
    """Raised when the judge answers something that is not a verdict."""


class _ClaimData(BaseModel):
    claim: str
    quote: str


class _VerdictData(BaseModel):
    claims: list[_ClaimData]


@dataclass(frozen=True)
class FaithfulnessVerdict:
    supported_claims: int
    unsupported_claims: tuple[str, ...]

    @property
    def total_claims(self) -> int:
        return self.supported_claims + len(self.unsupported_claims)

    @property
    def score(self) -> float:
        """Share of factual claims backed by a real quote: 1.0 when all of them are."""
        if self.total_claims == 0:
            return 1.0
        return self.supported_claims / self.total_claims

    @property
    def is_faithful(self) -> bool:
        return not self.unsupported_claims


class FaithfulnessJudge:
    def __init__(self, language_model: StructuredLanguageModel, instructions: str) -> None:
        self._language_model = language_model
        self._instructions = instructions

    def judge(self, discovery: Discovery, evidence: str) -> FaithfulnessVerdict:
        messages = [
            ChatMessage(role=Role.SYSTEM, content=self._instructions),
            ChatMessage(role=Role.USER, content=_case(discovery, evidence)),
        ]
        reply = self._language_model.complete_json(messages, VERDICT_SCHEMA)
        try:
            data = _VerdictData.model_validate(reply.data)
        except ValidationError as error:
            raise JudgeError(f"the judge did not answer with a verdict: {error}") from error
        supported = [item for item in data.claims if quote_is_in(item.quote, evidence)]
        unsupported = tuple(item.claim for item in data.claims if item not in supported)
        return FaithfulnessVerdict(len(supported), unsupported)


def quote_is_in(quote: str, evidence: str) -> bool:
    """True when the quote really appears in the pages (case, accents and punctuation aside).

    Very short quotes ("luz", "sim") would match almost anything, so they do not count.
    """
    normalized_quote = _normalized(quote)
    if len(normalized_quote.split()) < MIN_QUOTE_WORDS:
        return False
    return normalized_quote in _normalized(evidence)


def _normalized(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(NON_WORD.sub(" ", without_accents.lower()).split())


def _case(discovery: Discovery, evidence: str) -> str:
    return (
        f"PAGES:\n{evidence or '(no pages)'}\n\n"
        f"SAVED DISCOVERY:\nTitle: {discovery.title}\nTopic: {discovery.topic}\n"
        f"Summary: {discovery.summary}"
    )
