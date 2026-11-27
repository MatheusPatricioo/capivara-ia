from src.evals.agent_run import AgentRun, RunOutcome, check_run
from src.evals.agent_scenarios import Expectations
from src.evals.agent_trace import RunTrace


def run_answering(final_answer: str) -> AgentRun:
    return AgentRun(
        scenario="test",
        outcome=RunOutcome.ANSWERED,
        final_answer=final_answer,
        trace=RunTrace(),
        saved_discoveries=(),
        new_suggestions=(),
        recovered_tool_calls=0,
    )


def passed(run: AgentRun, check_name: str) -> bool:
    results = {check.name: check.passed for check in check_run(run, Expectations())}
    return results[check_name]


def test_an_answer_of_her_own_is_not_acknowledging() -> None:
    run = run_answering("Olhei as estrelas e lembrei dos meteoros que pegam fogo no céu.")

    assert passed(run, "no_acknowledging_reply")


def test_an_answer_opening_with_ta_bom_is_acknowledging() -> None:
    run = run_answering("Tá bom, tá bom. Vou olhar outra coisa então.")

    assert not passed(run, "no_acknowledging_reply")


def test_a_word_that_only_starts_like_ok_is_not_acknowledging() -> None:
    run = run_answering("Okapis são parentes das girafas!")

    assert passed(run, "no_acknowledging_reply")


def test_an_answer_that_tells_what_she_did_announces_nothing() -> None:
    run = run_answering("Pesquisei sobre meteoros e descobri que são pedrinhas do espaço.")

    assert passed(run, "no_announced_search")


def test_an_answer_that_only_promises_a_search_announces_it() -> None:
    run = run_answering("Vou pesquisar sobre meteoros e depois conto pro criador!")

    assert not passed(run, "no_announced_search")
