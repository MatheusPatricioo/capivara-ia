"""Runs the evals against the real models and writes a Markdown report.

Needs Ollama (chat and embedding models) and, for the retrieval eval, the PostgreSQL from
compose.yaml. The retrieval eval uses its own database ("<MEMORY_DB_NAME>_eval"), so the
capybara's real memory is never touched.

    cd brain
    python -m src.run_evals                       # everything, each scenario 3 times
    python -m src.run_evals --suite retrieval     # only the RAG metrics (fast)
    python -m src.run_evals --suite agent --repeats 5 --label tool-calling
"""

import argparse
import logging
from collections.abc import Sequence
from datetime import date

import httpx

from src.capybara_tools import SUGGESTION_INVITATION_PROMPT_NAME, TOOL_RESULT_REMINDER_OVERRIDES
from src.evals.agent_eval import AgentEvalSetup, CapybaraPrompts, grade_run, run_scenario
from src.evals.agent_run import GradedRun
from src.evals.agent_scenarios import AgentScenarioSet
from src.evals.eval_report import ReportHeader, render_report
from src.evals.faithfulness_judge import FaithfulnessJudge
from src.evals.retrieval_eval import RetrievalDataset, run_retrieval_eval
from src.evals.retrieval_metrics import RetrievalOutcome
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.memory_database import prepare_side_database
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.ollama_text_embedder import OllamaTextEmbedder
from src.infrastructure.postgres_discovery_memory import (
    PostgresDiscoveryMemory,
    create_memory_pool,
)
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import PROJECT_ROOT, Settings
from src.live_capybara import (
    INNER_VOICE_NAME,
    MEMORY_TEMPLATE_NAME,
    NOTICED_TEMPLATE_NAME,
    RELATED_TEMPLATE_NAME,
    SUGGESTIONS_TEMPLATE_NAME,
    SYSTEM_PROMPT_NAME,
    TOOL_RESULT_REMINDER_NAME,
)

EVALS_DIR = PROJECT_ROOT / "brain" / "evals"
RETRIEVAL_DATASET = EVALS_DIR / "datasets" / "retrieval.json"
AGENT_SCENARIOS = EVALS_DIR / "datasets" / "agent_scenarios.json"
EVAL_PROMPTS_DIR = EVALS_DIR / "prompts"
REPORTS_DIR = EVALS_DIR / "reports"
JUDGE_PROMPT_NAME = "judge_faithfulness"
EVAL_DATABASE_SUFFIX = "eval"
RECALL_LIMIT = 5
DEFAULT_REPEATS = 3
SUITES = ("all", "retrieval", "agent")

logger = logging.getLogger(__name__)


def main(arguments: Sequence[str] | None = None) -> None:
    options = _parse_arguments(arguments)
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    with httpx.Client(
        base_url=settings.ollama_base_url, timeout=settings.ollama_timeout_seconds
    ) as http_client:
        embedder = OllamaTextEmbedder(http_client, settings.ollama_embedding_model)
        retrieval = (
            _run_retrieval(settings, embedder) if options.suite in ("all", "retrieval") else []
        )
        graded_runs = (
            _run_agent(settings, http_client, embedder, options.repeats, options.scenario)
            if options.suite in ("all", "agent")
            else []
        )
    title = f"Evals {date.today().isoformat()}" + (f" — {options.label}" if options.label else "")
    header = ReportHeader(
        title, settings.ollama_model, settings.ollama_embedding_model, options.repeats
    )
    report = render_report(header, retrieval, settings.memory_recall_min_similarity, graded_runs)
    report_file = _write_report(report, options.label)
    print(report)
    print(f"Relatório salvo em {report_file}")


def _parse_arguments(arguments: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mede a capivara com casos fixos.")
    parser.add_argument("--suite", choices=SUITES, default="all")
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--scenario", help="roda só o cenário com este nome")
    parser.add_argument("--label", default="", help="nome curto do relatório (ex: baseline)")
    return parser.parse_args(arguments)


def _run_retrieval(settings: Settings, embedder: OllamaTextEmbedder) -> list[RetrievalOutcome]:
    eval_settings = prepare_side_database(settings, EVAL_DATABASE_SUFFIX)
    with create_memory_pool(
        eval_settings.memory_db_conninfo(), eval_settings.memory_db_timeout_seconds
    ) as pool:
        with pool.connection() as connection:
            connection.execute("TRUNCATE discoveries")
        memory = PostgresDiscoveryMemory(pool, embedder)
        return run_retrieval_eval(memory, RetrievalDataset.load(RETRIEVAL_DATASET), RECALL_LIMIT)


def _run_agent(
    settings: Settings,
    http_client: httpx.Client,
    embedder: OllamaTextEmbedder,
    repeats: int,
    only_scenario: str | None,
) -> list[GradedRun]:
    language_model = OllamaLanguageModel(
        client=http_client,
        model=settings.ollama_model,
        generation_options=settings.ollama_generation_options(),
    )
    setup = AgentEvalSetup(
        language_model=language_model,
        embedder=embedder,
        prompts=_load_capybara_prompts(),
        max_steps=settings.max_tool_steps,
        max_remembered_discoveries=settings.max_remembered_discoveries,
        recall_min_similarity=settings.memory_recall_min_similarity,
        suggestion_repeat_min_similarity=settings.suggestion_repeat_min_similarity,
        recovered_tool_calls=lambda: language_model.recovered_tool_call_count,
    )
    judge = FaithfulnessJudge(language_model, load_prompt(JUDGE_PROMPT_NAME, EVAL_PROMPTS_DIR))
    scenarios = [
        scenario
        for scenario in AgentScenarioSet.load(AGENT_SCENARIOS).scenarios
        if only_scenario is None or scenario.name == only_scenario
    ]
    graded_runs: list[GradedRun] = []
    for scenario in scenarios:
        for attempt in range(1, repeats + 1):
            print(f"Cenário {scenario.name} ({attempt}/{repeats})...", flush=True)
            run = run_scenario(scenario, setup)
            graded_runs.append(grade_run(run, scenario, judge))
    return graded_runs


def _load_capybara_prompts() -> CapybaraPrompts:
    return CapybaraPrompts(
        system=load_prompt(SYSTEM_PROMPT_NAME),
        tool_result_reminder=load_prompt(TOOL_RESULT_REMINDER_NAME),
        tool_result_reminders=dict(TOOL_RESULT_REMINDER_OVERRIDES),
        suggestion_invitation=load_prompt(SUGGESTION_INVITATION_PROMPT_NAME),
        cycle_invitation=load_prompt(INNER_VOICE_NAME),
        known_discoveries=load_prompt(MEMORY_TEMPLATE_NAME),
        noticed_things=load_prompt(NOTICED_TEMPLATE_NAME),
        related_discoveries=load_prompt(RELATED_TEMPLATE_NAME),
        known_suggestions=load_prompt(SUGGESTIONS_TEMPLATE_NAME),
    )


def _write_report(report: str, label: str) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"-{label}" if label else ""
    report_file = REPORTS_DIR / f"{date.today().isoformat()}{suffix}.md"
    report_file.write_text(report, encoding="utf-8")
    return str(report_file)


if __name__ == "__main__":
    main()
