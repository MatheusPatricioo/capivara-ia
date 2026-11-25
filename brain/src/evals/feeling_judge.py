"""LLM-as-judge: what feeling does her diary line show?

Like the faithfulness judge, it must show evidence: first the words of the diary that
carry the feeling, then the tone. The code checks the quote really is in the diary, so
the judge cannot invent a feeling she never wrote.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from src.domain.language_model import ChatMessage, Role, StructuredLanguageModel
from src.evals.faithfulness_judge import JudgeError, quote_is_in
from src.evals.feeling_scenarios import Tone

TONE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "quote": {
            "type": "string",
            "description": "The exact words of the diary that show how she feels, or ''.",
        },
        "tone": {"type": "string", "enum": [tone.value for tone in Tone]},
    },
    "required": ["quote", "tone"],
}


class _ToneData(BaseModel):
    quote: str
    tone: Tone


@dataclass(frozen=True)
class ToneVerdict:
    tone: Tone
    quote: str
    quote_found: bool
    """False when the judge quoted words that are not in the diary."""


class ToneJudge:
    def __init__(self, language_model: StructuredLanguageModel, instructions: str) -> None:
        self._language_model = language_model
        self._instructions = instructions

    def judge(self, diary_line: str) -> ToneVerdict:
        messages = [
            ChatMessage(role=Role.SYSTEM, content=self._instructions),
            ChatMessage(role=Role.USER, content=f"DIARY:\n{diary_line}"),
        ]
        reply = self._language_model.complete_json(messages, TONE_SCHEMA)
        try:
            data = _ToneData.model_validate(reply.data)
        except ValidationError as error:
            raise JudgeError(f"the judge did not answer with a tone: {error}") from error
        return ToneVerdict(data.tone, data.quote, quote_is_in(data.quote, diary_line))
