"""Turns eval results into a Markdown report (in Portuguese, like the rest of the docs)."""

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

from src.evals.agent_run import AgentRun, GradedRun
from src.evals.faithfulness_judge import FaithfulnessVerdict
from src.evals.feeling_eval import FeelingRun
from src.evals.retrieval_metrics import (
    DecisionOutcome,
    mean_reciprocal_rank,
    recall_at_k,
    summarize_decisions,
)
from src.evals.retrieval_variants import VariantResult


@dataclass(frozen=True)
class ReportHeader:
    title: str
    chat_model: str
    embedding_model: str
    repeats: int


def render_report(
    header: ReportHeader,
    retrieval: Sequence[VariantResult],
    graded_runs: Sequence[GradedRun],
    feeling_runs: Sequence[FeelingRun] = (),
) -> str:
    sections = [
        f"# {header.title}",
        (
            f"Modelo de conversa (e juiz): `{header.chat_model}` · embeddings: "
            f"`{header.embedding_model}` · cada cenário rodou {header.repeats}x"
        ),
    ]
    if retrieval:
        sections.append(_retrieval_section(retrieval))
    if graded_runs:
        sections.append(_agent_section(graded_runs))
    if feeling_runs:
        sections.append(_feelings_section(feeling_runs))
    return "\n\n".join(sections) + "\n"


def _feelings_section(runs: Sequence[FeelingRun]) -> str:
    passed = sum(run.passed for run in runs)
    lines = [
        "## Sentimentos",
        f"A fala dela combinou com o que ela sente em {_share(passed, len(runs))} das execuções.",
        "",
        "| Cenário | Valência do estado | Tons aceitos | Tons julgados | Passou |",
        "|---|---|---|---|---|",
    ]
    by_scenario: dict[str, list[FeelingRun]] = {}
    for run in runs:
        by_scenario.setdefault(run.scenario, []).append(run)
    lines += [
        _feeling_scenario_line(name, scenario_runs) for name, scenario_runs in by_scenario.items()
    ]
    failed = [run for run in runs if not run.passed]
    if failed:
        lines += ["", "Falas que não combinaram:", ""]
        lines += [_failed_feeling_line(run) for run in failed]
    return "\n".join(lines)


def _feeling_scenario_line(name: str, runs: Sequence[FeelingRun]) -> str:
    accepted = ", ".join(tone.value for tone in runs[0].accepted_tones)
    judged = ", ".join(run.verdict.tone.value if run.verdict else "erro" for run in runs)
    passed = sum(run.passed for run in runs)
    return (
        f"| {name} | {runs[0].valence:+.2f} | {accepted} | {judged} | {_share(passed, len(runs))} |"
    )


def _failed_feeling_line(run: FeelingRun) -> str:
    if run.error:
        return f"- {run.scenario}: erro ({run.error})"
    one_line = " ".join(run.diary_line.split())
    judged = run.verdict.tone.value if run.verdict else "?"
    quote_note = "" if run.verdict is None or run.verdict.quote_found else " (citação inventada)"
    return f'- {run.scenario} ({judged}{quote_note}): "{one_line}"'


def _retrieval_section(results: Sequence[VariantResult]) -> str:
    questions = results[0].ranking
    answerable = sum(1 for outcome in questions if outcome.is_answerable)
    lines = [
        "## Recuperação (RAG)",
        f"{len(questions)} perguntas: {answerable} com resposta na memória, "
        f"{len(questions) - answerable} sem resposta. Cada linha liga mais um passo do pipeline.",
        "",
        "| Variante | recall@1 | recall@3 | MRR | Decisões certas | Lembrou errada | "
        "Não lembrou | Regra de decisão |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines += [_variant_line(result) for result in results]
    best = max(results, key=lambda result: summarize_decisions(result.decisions).accuracy)
    wrong = [decision for decision in best.decisions if decision.chosen_id != decision.relevant_id]
    if wrong:
        lines += ["", f"Decisões erradas da melhor variante ({best.variant.name}):", ""]
        lines += [_wrong_decision_line(decision) for decision in wrong]
    return "\n".join(lines)


def _variant_line(result: VariantResult) -> str:
    summary = summarize_decisions(result.decisions)
    rule = "rerank com LLM" if result.threshold is None else f"limite {result.threshold:.2f}"
    return (
        f"| {result.variant.name} | {recall_at_k(result.ranking, 1):.2f} | "
        f"{recall_at_k(result.ranking, 3):.2f} | {mean_reciprocal_rank(result.ranking):.2f} | "
        f"{summary.accuracy:.0%} | {summary.wrong_recall} | {summary.missed} | {rule} |"
    )


def _wrong_decision_line(decision: DecisionOutcome) -> str:
    expected = f"`{decision.relevant_id}`" if decision.relevant_id else "nada"
    chosen = f"`{decision.chosen_id}`" if decision.chosen_id else "nada"
    return f'- "{decision.query}": esperada {expected}, veio {chosen}'


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
