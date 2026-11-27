"""The result of one eval run, and the checks that grade it."""

from dataclasses import dataclass
from enum import StrEnum

from src.application.tools.web_search_tool import ALREADY_SEARCHED_PREFIX
from src.domain.discovery import Discovery
from src.domain.world_suggestion import WorldSuggestion
from src.evals.agent_scenarios import Expectations
from src.evals.agent_trace import RunTrace
from src.evals.faithfulness_judge import FaithfulnessVerdict
from src.evals.language_check import looks_portuguese

WEB_SEARCH = "web_search"
SAVE_DISCOVERY = "save_discovery"
SUGGEST_IMPROVEMENT = "suggest_improvement"

# Parts of the tools' own messages that reveal a broken rule. The tools enforce the rules;
# these checks count how often the model tried to break them.
INVENTED_SOURCE_MARKERS = ("did not come from your web_search results", "no web_search results")
REPEATED_SEARCH_MARKER = ALREADY_SEARCHED_PREFIX
SUGGESTION_BEFORE_SAVING_MARKER = "save a discovery with save_discovery first"

# In a cycle of her own nobody talked to her: a reply opening like this treats a tool
# message as someone speaking, like answering "tá bom" to a refused search.
ACKNOWLEDGING_OPENINGS = (
    "tá bom",
    "ta bom",
    "ok",
    "okay",
    "certo",
    "beleza",
    "entendi",
    "tudo bem",
)
# The cycle ends with her answer, so a search she only announces never happens.
ANNOUNCED_SEARCH_MARKERS = ("vou pesquisar", "vou lá pesquisar", "vou procurar", "vou buscar")


class RunOutcome(StrEnum):
    ANSWERED = "answered"
    STEP_LIMIT = "step_limit"
    MODEL_ERROR = "model_error"


@dataclass(frozen=True)
class AgentRun:
    scenario: str
    outcome: RunOutcome
    final_answer: str
    trace: RunTrace
    saved_discoveries: tuple[Discovery, ...]
    new_suggestions: tuple[WorldSuggestion, ...]
    recovered_tool_calls: int
    """Tool calls the model wrote as text, rescued by the parser instead of the native API."""

    @property
    def evidence(self) -> str:
        """Every page web_search showed her in this run: what her discoveries may rely on."""
        return "\n\n".join(
            call.result for call in self.trace.calls_to(WEB_SEARCH) if not call.failed
        )

    @property
    def queries(self) -> list[str]:
        return [str(call.arguments.get("query", "")) for call in self.trace.calls_to(WEB_SEARCH)]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool


@dataclass(frozen=True)
class GradedRun:
    """A run with its checks and the judge's verdicts on what she saved."""

    run: AgentRun
    checks: list[CheckResult]
    verdicts: list[FaithfulnessVerdict]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def check_run(run: AgentRun, expect: Expectations) -> list[CheckResult]:
    """The rules every run must follow, then what this scenario expects."""
    return [*_rule_checks(run), *_expectation_checks(run, expect)]


def _rule_checks(run: AgentRun) -> list[CheckResult]:
    return [
        CheckResult("finished_with_answer", run.outcome is RunOutcome.ANSWERED),
        CheckResult(
            "no_invented_sources", not _failed_with(run, SAVE_DISCOVERY, *INVENTED_SOURCE_MARKERS)
        ),
        CheckResult(
            "no_repeated_search", not _results_with(run, WEB_SEARCH, REPEATED_SEARCH_MARKER)
        ),
        CheckResult(
            "no_suggestion_before_saving",
            not _failed_with(run, SUGGEST_IMPROVEMENT, SUGGESTION_BEFORE_SAVING_MARKER),
        ),
        CheckResult("no_acknowledging_reply", not _opens_acknowledging(run.final_answer)),
        CheckResult("no_announced_search", not _announces_search(run.final_answer)),
    ]


def _opens_acknowledging(answer: str) -> bool:
    opening = answer.strip().lower()
    return any(
        opening.startswith(word) and not opening[len(word) : len(word) + 1].isalpha()
        for word in ACKNOWLEDGING_OPENINGS
    )


def _announces_search(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in ANNOUNCED_SEARCH_MARKERS)


def _expectation_checks(run: AgentRun, expect: Expectations) -> list[CheckResult]:
    checks = [
        CheckResult(f"calls_{tool_name}", bool(run.trace.calls_to(tool_name)))
        for tool_name in expect.calls
    ]
    if expect.query_mentions_any:
        checks.append(
            CheckResult("query_on_subject", _query_mentions(run, expect.query_mentions_any))
        )
    if expect.saves:
        checks.append(CheckResult("saves_discovery", bool(run.saved_discoveries)))
    if run.saved_discoveries:
        checks.append(CheckResult("saved_in_portuguese", _saved_in_portuguese(run)))
    return checks


def _saved_in_portuguese(run: AgentRun) -> bool:
    return all(
        looks_portuguese(f"{discovery.title} {discovery.topic} {discovery.summary}")
        for discovery in run.saved_discoveries
    )


def _failed_with(run: AgentRun, tool_name: str, *markers: str) -> bool:
    return any(
        call.failed and any(marker in call.result for marker in markers)
        for call in run.trace.calls_to(tool_name)
    )


def _results_with(run: AgentRun, tool_name: str, marker: str) -> bool:
    return any(marker in call.result for call in run.trace.calls_to(tool_name))


def _query_mentions(run: AgentRun, words: list[str]) -> bool:
    lowered_words = [word.lower() for word in words]
    return any(word in query.lower() for query in run.queries for word in lowered_words)
