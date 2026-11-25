import pytest

from src.application.related_discoveries import RelatedDiscoveries
from src.domain.discovery_memory import DiscoveryMemory
from src.evals.retrieval_eval import EvalDiscovery, EvalQuestion, RetrievalDataset
from src.evals.retrieval_variants import CachedRewriter, RetrievalVariant, run_variant
from tests.fakes.in_memory_discovery_memory import InMemoryDiscoveryMemory, WordCountEmbedder

VOCABULARY = ["lua", "fases", "capivara", "nada", "água"]
THRESHOLD_VARIANT = RetrievalVariant("limite", False, False, False, rerank=False)
RERANK_VARIANT = RetrievalVariant("rerank", False, False, False, rerank=True)


class CountingRewriter:
    def __init__(self) -> None:
        self.calls = 0

    def expand(self, subject: str) -> str:
        self.calls += 1
        return f"{subject} reescrita"


@pytest.fixture
def dataset() -> RetrievalDataset:
    return RetrievalDataset(
        discoveries=[
            EvalDiscovery(id="lua", title="As fases da lua", topic="tema", summary="A lua"),
            EvalDiscovery(id="capivara", title="A capivara nada", topic="tema", summary="Água"),
        ],
        questions=[
            EvalQuestion(query="capivara na água", relevant_id="capivara"),
            EvalQuestion(query="fases da lua", relevant_id="lua"),
        ],
    )


def empty_memory(variant: RetrievalVariant) -> DiscoveryMemory:
    return InMemoryDiscoveryMemory(WordCountEmbedder(VOCABULARY))


def closest_above_half(variant: RetrievalVariant, memory: DiscoveryMemory) -> RelatedDiscoveries:
    return RelatedDiscoveries(memory, min_similarity=0.5)


def run(variant: RetrievalVariant, dataset: RetrievalDataset) -> list[str | None]:
    result = run_variant(
        variant, dataset, empty_memory, closest_above_half, CachedRewriter(CountingRewriter()), 2
    )
    return [decision.chosen_id for decision in result.decisions]


def test_cached_rewriter_rewrites_each_subject_only_once() -> None:
    rewriter = CountingRewriter()
    cached = CachedRewriter(rewriter)

    cached.expand("lua")
    cached.expand("lua")

    assert rewriter.calls == 1


def test_threshold_variant_reports_the_threshold_it_used(dataset: RetrievalDataset) -> None:
    result = run_variant(
        THRESHOLD_VARIANT,
        dataset,
        empty_memory,
        closest_above_half,
        CachedRewriter(CountingRewriter()),
        2,
    )

    assert result.threshold is not None


def test_threshold_variant_chooses_the_right_discoveries(dataset: RetrievalDataset) -> None:
    assert run(THRESHOLD_VARIANT, dataset) == ["capivara", "lua"]


def test_rerank_variant_decides_through_the_related_discoveries(
    dataset: RetrievalDataset,
) -> None:
    assert run(RERANK_VARIANT, dataset) == ["capivara", "lua"]
