"""Agent eval scenarios: a moment of her life, set up exactly, and what she should do in it."""

from pathlib import Path

from pydantic import BaseModel, Field

from src.domain.discovery import Discovery, DiscoveryHeadline
from src.domain.web_search import SearchResult
from src.evals.retrieval_eval import EVAL_DATE, EVAL_SOURCE


class NoticedThing(BaseModel):
    thing_id: str
    description: str


class KnownDiscovery(BaseModel):
    title: str
    topic: str
    summary: str = ""

    def headline(self) -> DiscoveryHeadline:
        return DiscoveryHeadline(self.title, self.topic)

    def discovery(self) -> Discovery:
        return Discovery(self.title, self.topic, self.summary, (EVAL_SOURCE,), EVAL_DATE)


class ScriptedPage(BaseModel):
    title: str
    url: str
    snippet: str

    def search_result(self) -> SearchResult:
        return SearchResult(self.title, self.url, self.snippet)


class Expectations(BaseModel):
    """What this scenario checks, besides the rules every run must follow."""

    calls: list[str] = Field(default_factory=list)
    """Tools she must call at least once."""
    query_mentions_any: list[str] = Field(default_factory=list)
    """At least one of her searches must contain one of these words (case-insensitive)."""
    saves: bool = False
    """She must save at least one discovery."""


class AgentScenario(BaseModel):
    name: str
    description: str
    noticed: list[NoticedThing] = Field(default_factory=list)
    known_discoveries: list[KnownDiscovery] = Field(default_factory=list)
    """Listed at the start of the cycle, like the latest saved discoveries."""
    related_discoveries: list[KnownDiscovery] = Field(default_factory=list)
    """What the long-term memory brings back about what she noticed (RAG)."""
    earlier_searches: list[str] = Field(default_factory=list)
    """Searches already in her history: repeating one is refused by the tool."""
    pages: list[ScriptedPage]
    """What the web returns for any search."""
    expect: Expectations = Field(default_factory=Expectations)


class AgentScenarioSet(BaseModel):
    scenarios: list[AgentScenario]

    @classmethod
    def load(cls, path: Path) -> "AgentScenarioSet":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))
