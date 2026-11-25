import pytest

from src.evals.agent_run import AgentRun, CheckResult, GradedRun, RunOutcome
from src.evals.agent_trace import RunTrace, ToolCallRecord
from src.evals.eval_report import ReportHeader, render_report
from src.evals.faithfulness_judge import FaithfulnessVerdict
from src.evals.retrieval_metrics import RetrievalOutcome

HEADER = ReportHeader("Evals de teste", "qwen2.5:7b", "nomic-embed-text", repeats=1)
THRESHOLD = 0.70


def a_graded_run(passed: bool) -> GradedRun:
    trace = RunTrace(
        model_replies=3,
        tokens=900,
        tool_calls=[ToolCallRecord("web_search", {"query": "lua"}, "1. Lua", failed=False)],
    )
    run = AgentRun("researches", RunOutcome.ANSWERED, "Aprendi.", trace, (), (), 0)
    verdict = FaithfulnessVerdict(
        supported_claims=1, unsupported_claims=("A lua é de queijo",)
    )
    return GradedRun(run, [CheckResult("finished_with_answer", passed)], [verdict])


@pytest.fixture
def report() -> str:
    retrieval = [RetrievalOutcome("lua no céu", "lua", ("lua", "sol"), (0.8, 0.6))]
    return render_report(HEADER, retrieval, THRESHOLD, [a_graded_run(True), a_graded_run(False)])


def test_shows_the_retrieval_metrics(report: str) -> None:
    assert "| recall@1 | 1.00 |" in report


def test_marks_the_current_threshold(report: str) -> None:
    assert "0.70 (atual)" in report


def test_shows_how_many_runs_passed_every_check(report: str) -> None:
    assert "| Execuções que passaram em tudo | 1/2 (50%) |" in report


def test_lists_the_claims_the_judge_did_not_find_in_the_pages(report: str) -> None:
    assert "- A lua é de queijo" in report


def test_leaves_out_the_agent_section_without_runs() -> None:
    report = render_report(HEADER, [], THRESHOLD, [])

    assert "## Agente" not in report
