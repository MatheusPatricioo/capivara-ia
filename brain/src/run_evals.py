"""Runs the evals against the real models and writes a Markdown report.

Needs Ollama (chat and embedding models) and, for the retrieval eval, the PostgreSQL from
compose.yaml. The retrieval eval uses its own database ("<MEMORY_DB_NAME>_eval"), so the
capybara's real memory is never touched.

    cd brain
    python -m src.run_evals                       # everything, each scenario 3 times
    python -m src.run_evals --suite retrieval     # only the RAG metrics (fast)
    python -m src.run_evals --suite agent --repeats 5 --label tool-calling
    python -m src.run_evals --suite feelings      # does what she writes match how she feels?
"""

import argparse
import logging
from collections.abc import Sequence
from datetime import date

import httpx

from src.application.memory_query_expander import MemoryQueryExpander
from src.application.related_discoveries import RelatedDiscoveries
from src.application.related_memory_chooser import RelatedMemoryChooser
from src.capybara_tools import SUGGESTION_INVITATION_PROMPT_NAME, TOOL_RESULT_REMINDER_OVERRIDES
from src.domain.discovery_memory import DiscoveryMemory
from src.evals.agent_eval import AgentEvalSetup, CapybaraPrompts, grade_run, run_scenario
from src.evals.agent_run import GradedRun
from src.evals.agent_scenarios import AgentScenarioSet
from src.evals.eval_report import ReportHeader, render_report
from src.evals.faithfulness_judge import FaithfulnessJudge
from src.evals.feeling_eval import FeelingPrompts, FeelingRun, run_feeling_scenario
from src.evals.feeling_judge import ToneJudge
from src.evals.feeling_scenarios import FeelingScenarioSet
from src.evals.retrieval_eval import RetrievalDataset
from src.evals.retrieval_variants import (
    CachedRewriter,
    RetrievalVariant,
    VariantResult,
    run_variant,
)
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.memory_database import prepare_side_database
from src.infrastructure.ollama_language_model import OllamaLanguageModel
from src.infrastructure.ollama_text_embedder import OllamaTextEmbedder
from src.infrastructure.postgres_discovery_memory import SearchMode, create_memory_pool
from src.infrastructure.prompt_loader import load_prompt
from src.infrastructure.settings import PROJECT_ROOT, Settings
from src.live_capybara import (
    FEELINGS_TEMPLATE_NAME,
    INNER_VOICE_NAME,
    MEMORY_TEMPLATE_NAME,
    NOTICED_TEMPLATE_NAME,
    RELATED_TEMPLATE_NAME,
    SUGGESTIONS_TEMPLATE_NAME,
    SYSTEM_PROMPT_NAME,
    TOOL_RESULT_REMINDER_NAME,
)
from src.long_term_memory import build_discovery_memory

EVALS_DIR = PROJECT_ROOT / "brain" / "evals"
RETRIEVAL_DATASET = EVALS_DIR / "datasets" / "retrieval.json"
AGENT_SCENARIOS = EVALS_DIR / "datasets" / "agent_scenarios.json"
EVAL_PROMPTS_DIR = EVALS_DIR / "prompts"
REPORTS_DIR = EVALS_DIR / "reports"
JUDGE_PROMPT_NAME = "judge_faithfulness"
EVAL_DATABASE_SUFFIX = "eval"
RECALL_LIMIT = 5
DEFAULT_REPEATS = 3
SUITES = ("all", "retrieval", "agent", "feelings")
FEELING_SCENARIOS = EVALS_DIR / "datasets" / "feeling_scenarios.json"
TONE_JUDGE_PROMPT_NAME = "judge_feeling_tone"
FEELING_DIARY_PROMPT_NAME = "feeling_diary"
EXPAND_MEMORY_QUERY_PROMPT_NAME = "expand_memory_query"
CHOOSE_RELATED_MEMORY_PROMPT_NAME = "choose_related_memory"
RETRIEVAL_VARIANTS = (
    RetrievalVariant("1. Vetor do texto inteiro (como era)", False, False, False, False),
    RetrievalVariant("2. + prefixos de tarefa", True, False, False, False),
    RetrievalVariant("3. + chunks e busca híbrida (RRF)", True, True, False, False),
    RetrievalVariant("4. + reescrita da pergunta", True, True, True, False),
    RetrievalVariant("5. + rerank com LLM", True, True, True, True),
    RetrievalVariant("6. Híbrida + rerank, sem reescrita", True, True, False, True),
)

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
            _run_retrieval(settings, http_client, embedder)
            if options.suite in ("all", "retrieval")
            else []
        )
        graded_runs = (
            _run_agent(settings, http_client, embedder, options.repeats, options.scenario)
            if options.suite in ("all", "agent")
            else []
        )
        feeling_runs = (
            _run_feelings(settings, http_client, options.repeats, options.scenario)
            if options.suite in ("all", "feelings")
            else []
        )
    title = f"Evals {date.today().isoformat()}" + (f" — {options.label}" if options.label else "")
    header = ReportHeader(
        title, settings.ollama_model, settings.ollama_embedding_model, options.repeats
    )
    report = render_report(header, retrieval, graded_runs, feeling_runs)
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


def _run_retrieval(
    settings: Settings, http_client: httpx.Client, embedder: OllamaTextEmbedder
) -> list[VariantResult]:
    """Runs every RAG variant on its own empty eval database, the same questions each time."""
    judge_model = OllamaLanguageModel(client=http_client, model=settings.ollama_model)
    rewriter = CachedRewriter(
        MemoryQueryExpander(judge_model, load_prompt(EXPAND_MEMORY_QUERY_PROMPT_NAME))
    )
    chooser = RelatedMemoryChooser(judge_model, load_prompt(CHOOSE_RELATED_MEMORY_PROMPT_NAME))
    dataset = RetrievalDataset.load(RETRIEVAL_DATASET)
    eval_settings = prepare_side_database(settings, EVAL_DATABASE_SUFFIX)
    with create_memory_pool(
        eval_settings.memory_db_conninfo(), eval_settings.memory_db_timeout_seconds
    ) as pool:

        def empty_memory(variant: RetrievalVariant) -> DiscoveryMemory:
            with pool.connection() as connection:
                connection.execute("TRUNCATE discoveries CASCADE")
            return build_discovery_memory(
                pool,
                embedder,
                task_prefixes=variant.task_prefixes,
                search_mode=SearchMode.HYBRID if variant.hybrid_search else SearchMode.VECTOR,
            )

        def related(variant: RetrievalVariant, memory: DiscoveryMemory) -> RelatedDiscoveries:
            return RelatedDiscoveries(
                memory,
                settings.memory_recall_min_similarity,
                chooser=chooser,
                expander=rewriter if variant.query_rewriting else None,
            )

        results = []
        for variant in RETRIEVAL_VARIANTS:
            print(f"RAG: {variant.name}...", flush=True)
            results.append(
                run_variant(variant, dataset, empty_memory, related, rewriter, RECALL_LIMIT)
            )
        return results


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
        recall_tool=settings.memory_recall_tool,
        suggestion_repeat_min_similarity=settings.suggestion_repeat_min_similarity,
        recovered_tool_calls=lambda: language_model.recovered_tool_call_count,
    )
    judge = FaithfulnessJudge(language_model, load_prompt(JUDGE_PROMPT_NAME, EVAL_PROMPTS_DIR))
    scenarios = [
        scenario
        for scenario in AgentScenarioSet.load(AGENT_SCENARIOS).scenarios
        if only_scenario is None or scenario.name == only_scenario
        # Without the tool, a scenario that expects it could only fail.
        if settings.memory_recall_tool or not scenario.needs_recall_tool()
    ]
    graded_runs: list[GradedRun] = []
    for scenario in scenarios:
        for attempt in range(1, repeats + 1):
            print(f"Cenário {scenario.name} ({attempt}/{repeats})...", flush=True)
            run = run_scenario(scenario, setup)
            graded_runs.append(grade_run(run, scenario, judge))
    return graded_runs


def _run_feelings(
    settings: Settings, http_client: httpx.Client, repeats: int, only_scenario: str | None
) -> list[FeelingRun]:
    language_model = OllamaLanguageModel(
        client=http_client,
        model=settings.ollama_model,
        generation_options=settings.ollama_generation_options(),
    )
    judge = ToneJudge(language_model, load_prompt(TONE_JUDGE_PROMPT_NAME, EVAL_PROMPTS_DIR))
    prompts = FeelingPrompts(
        system=load_prompt(SYSTEM_PROMPT_NAME),
        feelings_template=load_prompt(FEELINGS_TEMPLATE_NAME),
        diary_invitation=load_prompt(FEELING_DIARY_PROMPT_NAME, EVAL_PROMPTS_DIR),
    )
    scenarios = [
        scenario
        for scenario in FeelingScenarioSet.load(FEELING_SCENARIOS).scenarios
        if only_scenario is None or scenario.name == only_scenario
    ]
    runs: list[FeelingRun] = []
    for scenario in scenarios:
        for attempt in range(1, repeats + 1):
            print(f"Sentimentos: {scenario.name} ({attempt}/{repeats})...", flush=True)
            runs.append(run_feeling_scenario(scenario, language_model, judge, prompts))
    return runs


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
