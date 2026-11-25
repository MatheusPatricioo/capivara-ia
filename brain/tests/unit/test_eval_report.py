import pytest

from src.evals.agent_run import AgentRun, CheckResult, GradedRun, RunOutcome
from src.evals.agent_trace import RunTrace, ToolCallRecord
from src.evals.eval_report import ReportHeader, render_report
from src.evals.faithfulness_judge import FaithfulnessVerdict
from src.evals.retrieval_metrics import DecisionOutcome, RetrievalOutcome
from src.evals.retrieval_variants import RetrievalVariant, VariantResult

HEADER = ReportHeader("Evals de teste", "qwen2.5:7b", "nomic-embed-text", repeats=1)
RANKING = [RetrievalOutcome("lua no céu", "lua", ("lua", "sol"), (0.8, 0.6))]


def a_graded_run(passed: bool) -> GradedRun:
    trace = RunTrace(
        model_replies=3,
        tokens=900,
        tool_calls=[ToolCallRecord("web_search", {"query": "lua"}, "1. Lua", failed=False)],
    )
    run = AgentRun("researches", RunOutcome.ANSWERED, "Aprendi.", trace, (), (), 0)
    verdict = FaithfulnessVerdict(supported_claims=1, unsupported_claims=("A lua é de queijo",))
    return GradedRun(run, [CheckResult("finished_with_answer", passed)], [verdict])


def a_variant_result(name: str, chosen_id: str | None, threshold: float | None) -> VariantResult:
    variant = RetrievalVariant(name, True, True, False, threshold is None)
    decisions = [DecisionOutcome("lua no céu", "lua", chosen_id)]
    return VariantResult(variant, RANKING, decisions, threshold)


@pytest.fixture
def report() -> str:
    retrieval = [
        a_variant_result("1. Vetor", chosen_id="sol", threshold=0.6),
        a_variant_result("2. Rerank", chosen_id="lua", threshold=None),
    ]
    return render_report(HEADER, retrieval, [a_graded_run(True), a_graded_run(False)])


def test_shows_one_line_per_rag_variant(report: str) -> None:
    assert "| 1. Vetor | 1.00 | 1.00 | 1.00 | 0% | 1 | 0 | limite 0.60 |" in report


def test_names_the_decision_rule_of_rerank_variants(report: str) -> None:
    assert "| 2. Rerank | 1.00 | 1.00 | 1.00 | 100% | 0 | 0 | rerank com LLM |" in report


def test_shows_how_many_runs_passed_every_check(report: str) -> None:
    assert "| Execuções que passaram em tudo | 1/2 (50%) |" in report


def test_lists_the_claims_the_judge_did_not_find_in_the_pages(report: str) -> None:
    assert "- A lua é de queijo" in report


def test_leaves_out_the_agent_section_without_runs() -> None:
    report = render_report(HEADER, [], [])

    assert "## Agente" not in report
