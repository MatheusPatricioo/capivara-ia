"""Retrieval eval: loads a fixed set of discoveries into the memory and asks known questions."""

from datetime import date
from pathlib import Path

from pydantic import BaseModel, model_validator

from src.domain.discovery import Discovery
from src.domain.discovery_memory import DiscoveryMemory
from src.evals.retrieval_metrics import RetrievalOutcome

EVAL_SOURCE = "https://example.com/eval"
EVAL_DATE = date(2026, 1, 1)


class EvalDiscovery(BaseModel):
    id: str
    title: str
    topic: str
    summary: str

    def to_discovery(self) -> Discovery:
        return Discovery(
            title=self.title,
            topic=self.topic,
            summary=self.summary,
            sources=(EVAL_SOURCE,),
            discovered_on=EVAL_DATE,
        )


class EvalQuestion(BaseModel):
    query: str
    relevant_id: str | None
    """The discovery that answers the question; null when none does."""


class RetrievalDataset(BaseModel):
    discoveries: list[EvalDiscovery]
    questions: list[EvalQuestion]

    @model_validator(mode="after")
    def _check_references(self) -> "RetrievalDataset":
        ids = [discovery.id for discovery in self.discoveries]
        titles = [discovery.title for discovery in self.discoveries]
        if len(set(ids)) != len(ids) or len(set(titles)) != len(titles):
            raise ValueError("discovery ids and titles must be unique")
        unknown = {
            question.relevant_id
            for question in self.questions
            if question.relevant_id is not None and question.relevant_id not in ids
        }
        if unknown:
            raise ValueError(f"questions point at unknown discoveries: {sorted(unknown)}")
        return self

    @classmethod
    def load(cls, path: Path) -> "RetrievalDataset":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


def run_retrieval_eval(
    memory: DiscoveryMemory, dataset: RetrievalDataset, limit: int
) -> list[RetrievalOutcome]:
    """Remembers every discovery of the dataset, then recalls each question.

    The memory must start empty: anything else in it would count as a wrong answer.
    """
    id_by_title = {discovery.title: discovery.id for discovery in dataset.discoveries}
    for discovery in dataset.discoveries:
        memory.remember(discovery.id, discovery.to_discovery())
    outcomes: list[RetrievalOutcome] = []
    for question in dataset.questions:
        remembered = memory.recall(question.query, limit)
        outcomes.append(
            RetrievalOutcome(
                query=question.query,
                relevant_id=question.relevant_id,
                ranked_ids=tuple(id_by_title[item.discovery.title] for item in remembered),
                similarities=tuple(item.similarity for item in remembered),
            )
        )
    return outcomes
