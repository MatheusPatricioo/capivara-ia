"""Turns eval results into a Markdown report (in Portuguese, like the rest of the docs)."""

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

from src.evals.agent_run import AgentRun, GradedRun
from src.evals.faithfulness_judge import FaithfulnessVerdict
from src.evals.retrieval_metrics import (
    RetrievalOutcome,
    mean_reciprocal_rank,
    recall_at_k,
    threshold_decisions,
)

THRESHOLD_SWEEP = (0.60, 0.65, 0.70, 0.75, 0.80)


@dataclass(frozen=True)
class ReportHeader:
    title: str
    chat_model: str
    embedding_model: str
    repeats: int


def render_report(
    header: ReportHeader,
    retrieval: Sequence[RetrievalOutcome],
    recall_threshold: float,
    graded_runs: Sequence[GradedRun],
) -> str:
    sections = [
        f"# {header.title}",
        (
            f"Modelo de conversa (e juiz): `{header.chat_model}` · embeddings: "
            f"`{header.embedding_model}` · cada cenário rodou {header.repeats}x"
        ),
    ]
    if retrieval:
        sections.append(_retrieval_section(retrieval, recall_threshold))
    if graded_runs:
        sections.append(_agent_section(graded_runs))
    return "\n\n".join(sections) + "\n"


def _retrieval_section(outcomes: Sequence[RetrievalOutcome], threshold: float) -> str:
    answerable = sum(1 for outcome in outcomes if outcome.is_answerable)
    lines = [
        "## Recuperação (RAG)",
        f"{len(outcomes)} perguntas: {answerable} com resposta na memória, "
        f"{len(outcomes) - answerable} sem resposta.",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| recall@1 | {recall_at_k(outcomes, 1):.2f} |",
        f"| recall@3 | {recall_at_k(outcomes, 3):.2f} |",
        f"| MRR | {mean_reciprocal_rank(outcomes):.2f} |",
        "",
        'Decisão "só a mais parecida, e só acima do limite" (o que vai para o contexto dela):',
        "",
        "| Limite | Acerto | Lembrou a certa | Lembrou errada | Não lembrou | Silêncio certo |",
        "|---|---|---|---|---|---|",
    ]
    for value in sorted({*THRESHOLD_SWEEP, threshold}):
        decisions = threshold_decisions(outcomes, value)
        marker = " (atual)" if value == threshold else ""
        lines.append(
            f"| {value:.2f}{marker} | {decisions.accuracy:.0%} | {decisions.right_recall} | "
            f"{decisions.wrong_recall} | {decisions.missed} | {decisions.right_silence} |"
        )
    misses = [outcome for outcome in outcomes if outcome.is_answerable and outcome.rank != 1]
    if misses:
        lines += ["", "Perguntas em que a certa não veio em 1º:", ""]
        lines += [_miss_line(outcome) for outcome in misses]
    return "\n".join(lines)


def _miss_line(outcome: RetrievalOutcome) -> str:
    first = outcome.ranked_ids[0] if outcome.ranked_ids else "nada"
    rank = outcome.rank if outcome.rank is not None else "fora"
    return (
        f'- "{outcome.query}": esperada `{outcome.relevant_id}` (posição {rank}), '
        f"veio `{first}` ({outcome.top_similarity:.3f})"
    )


def _agent_section(graded_runs: Sequence[GradedRun]) -> str:
    runs = [graded.run for graded in graded_runs]
    verdicts = [verdict for graded in graded_runs for verdict in graded.verdicts]
    tool_calls = [call for run in runs for call in run.trace.tool_calls]
    recovered = sum(run.recovered_tool_calls for run in runs)
    passed_runs = sum(graded.passed for graded in graded_runs)
    refused_calls = sum(call.failed for call in tool_calls)
    faithful = sum(verdict.is_faithful for verdict in verdicts)
    metrics = [
        ("Execuções que passaram em tudo", _share(passed_runs, len(runs))),
        ("Respostas do modelo por execução (média)", f"{mean(_replies(runs)):.1f}"),
        ("Tokens por execução (média)", f"{mean(run.trace.tokens for run in runs):.0f}"),
        ("Chamadas de ferramenta", str(len(tool_calls))),
        ("Chamadas recusadas pela ferramenta", _share(refused_calls, len(tool_calls))),
        ("Chamadas escritas como texto (resgatadas)", _share(recovered, len(tool_calls))),
        ("Descobertas julgadas", str(len(verdicts))),
        ("Fiéis às páginas (juiz)", _share(faithful, len(verdicts))),
        ("Afirmações com citação nas páginas (média)", _mean_score(verdicts)),
    ]
    lines = ["## Agente", "", "| Métrica | Valor |", "|---|---|"]
    lines += [f"| {label} | {value} |" for label, value in metrics]
    lines += ["", "| Checagem | Passou |", "|---|---|"]
    lines += [f"| {name} | {share} |" for name, share in _check_shares(graded_runs)]
    lines += ["", "| Cenário | Passou em tudo |", "|---|---|"]
    lines += [f"| {name} | {share} |" for name, share in _scenario_shares(graded_runs)]
    unsupported = [claim for verdict in verdicts for claim in verdict.unsupported_claims]
    if unsupported:
        lines += ["", "Afirmações sem apoio nas páginas, segundo o juiz:", ""]
        lines += [f"- {claim}" for claim in unsupported]
    return "\n".join(lines)


def _check_shares(graded_runs: Sequence[GradedRun]) -> list[tuple[str, str]]:
    results: dict[str, list[bool]] = {}
    for graded in graded_runs:
        for check in graded.checks:
            results.setdefault(check.name, []).append(check.passed)
    return [(name, _share(sum(passed), len(passed))) for name, passed in results.items()]


def _scenario_shares(graded_runs: Sequence[GradedRun]) -> list[tuple[str, str]]:
    results: dict[str, list[bool]] = {}
    for graded in graded_runs:
        results.setdefault(graded.run.scenario, []).append(graded.passed)
    return [(name, _share(sum(passed), len(passed))) for name, passed in results.items()]


def _share(count: int, total: int) -> str:
    if total == 0:
        return "—"
    return f"{count}/{total} ({count / total:.0%})"


def _mean_score(verdicts: Sequence[FaithfulnessVerdict]) -> str:
    if not verdicts:
        return "—"
    return f"{mean(verdict.score for verdict in verdicts):.0%}"


def _replies(runs: Sequence[AgentRun]) -> list[int]:
    return [run.trace.model_replies for run in runs]
