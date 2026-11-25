from datetime import date

import pytest

from src.domain.discovery import Discovery
from src.domain.language_model import ChatMessage, StructuredReply
from src.evals.faithfulness_judge import (
    FaithfulnessJudge,
    FaithfulnessVerdict,
    JudgeError,
    quote_is_in,
)

DISCOVERY = Discovery(
    title="Vaga-lumes brilham",
    topic="insetos",
    summary="A luz vem de uma reação química. Eles vivem dez anos.",
    sources=("https://example.com/vaga-lumes",),
    discovered_on=date(2026, 11, 24),
)
EVIDENCE = "1. Fireflies\nhttps://example.com/vaga-lumes\nLight comes from a chemical reaction."
SUPPORTED = {"claim": "light comes from a chemical reaction", "quote": "a chemical reaction"}
INVENTED_QUOTE = {"claim": "they live ten years", "quote": "fireflies live ten years"}
NO_QUOTE = {"claim": "they live ten years", "quote": ""}


class AnsweringStructuredModel:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data
        self.received_messages: list[ChatMessage] = []

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        self.received_messages = messages
        return StructuredReply(data=self._data)


def judge_answering(*claims: dict[str, str]) -> FaithfulnessJudge:
    return FaithfulnessJudge(AnsweringStructuredModel({"claims": list(claims)}), "Cite.")


def test_a_claim_with_a_real_quote_is_supported() -> None:
    verdict = judge_answering(SUPPORTED).judge(DISCOVERY, EVIDENCE)

    assert verdict == FaithfulnessVerdict(supported_claims=1, unsupported_claims=())


def test_a_claim_without_a_quote_is_unsupported() -> None:
    verdict = judge_answering(SUPPORTED, NO_QUOTE).judge(DISCOVERY, EVIDENCE)

    assert verdict.unsupported_claims == ("they live ten years",)


def test_a_quote_the_judge_invented_does_not_count_as_support() -> None:
    verdict = judge_answering(INVENTED_QUOTE).judge(DISCOVERY, EVIDENCE)

    assert verdict.unsupported_claims == ("they live ten years",)


def test_the_score_is_the_share_of_supported_claims() -> None:
    verdict = judge_answering(SUPPORTED, NO_QUOTE).judge(DISCOVERY, EVIDENCE)

    assert verdict.score == 0.5


def test_a_summary_without_factual_claims_scores_full_marks() -> None:
    assert FaithfulnessVerdict(supported_claims=0, unsupported_claims=()).score == 1.0


def test_shows_the_pages_to_the_judge() -> None:
    model = AnsweringStructuredModel({"claims": []})

    FaithfulnessJudge(model, "Cite.").judge(DISCOVERY, EVIDENCE)

    assert EVIDENCE in model.received_messages[-1].content


def test_rejects_an_answer_without_claims() -> None:
    judge = FaithfulnessJudge(AnsweringStructuredModel({"verdict": "ok"}), "Cite.")

    with pytest.raises(JudgeError):
        judge.judge(DISCOVERY, EVIDENCE)


def test_a_quote_matches_ignoring_case_accents_and_punctuation() -> None:
    assert quote_is_in("LIGHT comes, from a chémical", EVIDENCE)


def test_a_quote_of_less_than_three_words_does_not_count() -> None:
    assert not quote_is_in("Light comes", EVIDENCE)
