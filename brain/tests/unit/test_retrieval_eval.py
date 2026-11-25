import pytest
from pydantic import ValidationError

from src.evals.retrieval_eval import (
    EvalDiscovery,
    EvalQuestion,
    RetrievalDataset,
    run_retrieval_eval,
)
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder

VOCABULARY = ["lua", "fases", "capivara", "nada", "água"]


def a_discovery(identifier: str, title: str, summary: str) -> EvalDiscovery:
    return EvalDiscovery(id=identifier, title=title, topic="tema", summary=summary)


@pytest.fixture
def dataset() -> RetrievalDataset:
    return RetrievalDataset(
        discoveries=[
            a_discovery("lua", "As fases da lua", "A lua tem fases"),
            a_discovery("capivara", "A capivara nada", "A capivara nada na água"),
        ],
        questions=[
            EvalQuestion(query="capivara na água", relevant_id="capivara"),
            EvalQuestion(query="fases da lua", relevant_id="lua"),
        ],
    )


def test_ranks_the_closest_discovery_first(dataset: RetrievalDataset) -> None:
    memory = InMemoryDiscoveryMemory(WordCountEmbedder(VOCABULARY))

    outcomes = run_retrieval_eval(memory, dataset, limit=2)

    assert [outcome.ranked_ids[0] for outcome in outcomes] == ["capivara", "lua"]


def test_keeps_the_expected_answer_of_each_question(dataset: RetrievalDataset) -> None:
    memory = InMemoryDiscoveryMemory(WordCountEmbedder(VOCABULARY))

    outcomes = run_retrieval_eval(memory, dataset, limit=2)

    assert [outcome.relevant_id for outcome in outcomes] == ["capivara", "lua"]


def test_rejects_a_question_pointing_at_an_unknown_discovery() -> None:
    with pytest.raises(ValidationError, match="unknown discoveries"):
        RetrievalDataset(
            discoveries=[a_discovery("lua", "Lua", "Lua")],
            questions=[EvalQuestion(query="sol", relevant_id="sol")],
        )


def test_rejects_two_discoveries_with_the_same_title() -> None:
    with pytest.raises(ValidationError, match="unique"):
        RetrievalDataset(
            discoveries=[a_discovery("lua", "Lua", "A"), a_discovery("lua-2", "Lua", "B")],
            questions=[],
        )
