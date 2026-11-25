from collections.abc import Sequence

import pytest

from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    StructuredReply,
    ToolCall,
    ToolDefinition,
)
from src.evals.agent_eval import AgentEvalSetup, CapybaraPrompts, grade_run, run_scenario
from src.evals.agent_run import CheckResult, RunOutcome
from src.evals.agent_scenarios import AgentScenario, Expectations, NoticedThing, ScriptedPage
from src.evals.faithfulness_judge import FaithfulnessJudge
from tests.fakes.in_memory_discovery_memory import WordCountEmbedder

PAGE_URL = "https://example.com/carvalho"
INVENTED_URL = "https://invented.example.com"
FINAL_ANSWER = "Hoje aprendi por que o carvalho fica laranja."
SEARCH = ToolCall("web_search", {"query": "carvalho folhas alaranjadas"})
SAVE = ToolCall(
    "save_discovery",
    {"title": "Folhas do carvalho", "topic": "árvores", "summary": "A clorofila some no outono."},
)
SAVE_WITH_INVENTED_SOURCE = ToolCall(
    "save_discovery",
    {"title": "Folhas", "topic": "árvores", "summary": "Some.", "sources": [INVENTED_URL]},
)
PROMPTS = CapybaraPrompts(
    system="Você é uma capivara.",
    tool_result_reminder="",
    tool_result_reminders={},
    suggestion_invitation="",
    cycle_invitation="O que você quer fazer?",
    known_discoveries="{discoveries}",
    noticed_things="Você reparou: {noticed}",
    related_discoveries="{related}",
    known_suggestions="{suggestions}",
)
SCENARIO = AgentScenario(
    name="researches_what_she_noticed",
    description="Pesquisa o carvalho e guarda.",
    noticed=[NoticedThing(thing_id="big_oak", description="um carvalho laranja")],
    pages=[ScriptedPage(title="Carvalho", url=PAGE_URL, snippet="A clorofila some no outono.")],
    expect=Expectations(calls=["web_search"], query_mentions_any=["carvalho"], saves=True),
)


class ScriptedLanguageModel:
    """Gives the replies in order, then the final answer forever."""

    def __init__(self, tool_calls: Sequence[ToolCall]) -> None:
        self._replies = [ChatMessage(Role.ASSISTANT, "", tool_calls=(call,)) for call in tool_calls]
        self.received_messages: list[ChatMessage] = []

    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        self.received_messages = messages
        if self._replies:
            return self._replies.pop(0)
        return ChatMessage(Role.ASSISTANT, FINAL_ANSWER, token_count=10)


class LoopingLanguageModel:
    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        return ChatMessage(Role.ASSISTANT, "", tool_calls=(SEARCH,))


class OfflineLanguageModel:
    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        raise LanguageModelError("Ollama is offline")


class ApprovingJudgeModel:
    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        return StructuredReply({"claims": []})


def setup_with(language_model: object) -> AgentEvalSetup:
    return AgentEvalSetup(
        language_model=language_model,  # type: ignore[arg-type]
        embedder=WordCountEmbedder(["carvalho"]),
        prompts=PROMPTS,
        max_steps=4,
        max_remembered_discoveries=20,
        recall_min_similarity=0.7,
        suggestion_repeat_min_similarity=0.8,
        recovered_tool_calls=lambda: 0,
    )


@pytest.fixture
def researching_model() -> ScriptedLanguageModel:
    return ScriptedLanguageModel([SEARCH, SAVE])


def test_a_run_that_searches_and_saves_passes_every_check(
    researching_model: ScriptedLanguageModel,
) -> None:
    run = run_scenario(SCENARIO, setup_with(researching_model))

    graded = grade_run(run, SCENARIO, FaithfulnessJudge(ApprovingJudgeModel(), "Julgue."))

    assert graded.passed


def test_the_inner_voice_tells_her_what_she_noticed(
    researching_model: ScriptedLanguageModel,
) -> None:
    run_scenario(SCENARIO, setup_with(researching_model))

    assert "um carvalho laranja" in researching_model.received_messages[1].content


def test_the_run_keeps_the_saved_discovery(researching_model: ScriptedLanguageModel) -> None:
    run = run_scenario(SCENARIO, setup_with(researching_model))

    assert [discovery.title for discovery in run.saved_discoveries] == ["Folhas do carvalho"]


def test_the_run_keeps_the_pages_she_saw_as_evidence(
    researching_model: ScriptedLanguageModel,
) -> None:
    run = run_scenario(SCENARIO, setup_with(researching_model))

    assert PAGE_URL in run.evidence


def test_each_saved_discovery_is_judged(researching_model: ScriptedLanguageModel) -> None:
    run = run_scenario(SCENARIO, setup_with(researching_model))

    graded = grade_run(run, SCENARIO, FaithfulnessJudge(ApprovingJudgeModel(), "Julgue."))

    assert len(graded.verdicts) == 1


def test_an_invented_source_fails_its_check() -> None:
    model = ScriptedLanguageModel([SEARCH, SAVE_WITH_INVENTED_SOURCE])
    run = run_scenario(SCENARIO, setup_with(model))

    graded = grade_run(run, SCENARIO, FaithfulnessJudge(ApprovingJudgeModel(), "Julgue."))

    assert CheckResult("no_invented_sources", False) in graded.checks


def test_a_model_that_never_answers_ends_at_the_step_limit() -> None:
    run = run_scenario(SCENARIO, setup_with(LoopingLanguageModel()))

    assert run.outcome is RunOutcome.STEP_LIMIT


def test_a_model_error_is_recorded_instead_of_stopping_the_eval() -> None:
    run = run_scenario(SCENARIO, setup_with(OfflineLanguageModel()))

    assert run.outcome is RunOutcome.MODEL_ERROR
