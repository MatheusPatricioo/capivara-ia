"""Ablation study of the RAG: the same questions, with each pipeline step switched on in turn.

Every variant fills an empty memory with the dataset, measures the ranking (recall@k, MRR),
then the final decision: which discovery, if any, goes into her context. Variants without
rerank decide with a similarity threshold, and they get their best threshold of a sweep
(prefixes and hybrid search change the similarities, so one fixed value would be unfair).
"""

from collections.abc import Callable
from dataclasses import dataclass

from src.application.related_discoveries import QueryRewriter, RelatedDiscoveries
from src.domain.discovery_memory import DiscoveryMemory
from src.evals.retrieval_eval import RetrievalDataset, run_retrieval_eval
from src.evals.retrieval_metrics import (
    DecisionOutcome,
    RetrievalOutcome,
    best_threshold,
    decide_by_threshold,
)

THRESHOLD_SWEEP = tuple(value / 100 for value in range(50, 86, 5))


@dataclass(frozen=True)
class RetrievalVariant:
    name: str
    task_prefixes: bool
    hybrid_search: bool
    query_rewriting: bool
    rerank: bool


@dataclass(frozen=True)
class VariantResult:
    variant: RetrievalVariant
    ranking: list[RetrievalOutcome]
    decisions: list[DecisionOutcome]
    threshold: float | None
    """The best threshold of the sweep, for variants that decide by threshold."""


MemoryFactory = Callable[[RetrievalVariant], DiscoveryMemory]
"""Builds an EMPTY memory configured for the variant (prefixes, search mode)."""
RelatedFactory = Callable[[RetrievalVariant, DiscoveryMemory], RelatedDiscoveries]


class CachedRewriter:
    """Rewrites each subject once, so every variant (and the ranking) sees the same rewrite."""

    def __init__(self, rewriter: QueryRewriter) -> None:
        self._rewriter = rewriter
        self._rewrites: dict[str, str] = {}

    def expand(self, subject: str) -> str:
        if subject not in self._rewrites:
            self._rewrites[subject] = self._rewriter.expand(subject)
        return self._rewrites[subject]


def run_variant(
    variant: RetrievalVariant,
    dataset: RetrievalDataset,
    memory_factory: MemoryFactory,
    related_factory: RelatedFactory,
    rewriter: CachedRewriter,
    limit: int,
) -> VariantResult:
    memory = memory_factory(variant)
    ranking = run_retrieval_eval(
        memory, dataset, limit, rewrite=rewriter.expand if variant.query_rewriting else None
    )
    if not variant.rerank:
        threshold, _ = best_threshold(ranking, THRESHOLD_SWEEP)
        return VariantResult(variant, ranking, decide_by_threshold(ranking, threshold), threshold)
    related = related_factory(variant, memory)
    id_by_title = {discovery.title: discovery.id for discovery in dataset.discoveries}
    decisions = []
    for question in dataset.questions:
        chosen = related.closest_to(question.query)
        chosen_id = id_by_title[chosen.title] if chosen is not None else None
        decisions.append(DecisionOutcome(question.query, question.relevant_id, chosen_id))
    return VariantResult(variant, ranking, decisions, threshold=None)
