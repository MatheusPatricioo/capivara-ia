"""Agent eval: runs each scenario with the real model, tools, prompts and inner voice."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from src.application.attention_inbox import AttentionInbox
from src.application.chalkboard_artist import PinnedDrawing
from src.application.conversation import Conversation, StepLimitReachedError
from src.application.inner_voice import InnerVoice
from src.application.related_discoveries import RelatedDiscoveries
from src.application.repeated_suggestions import RepeatedSuggestions
from src.application.tools.conversation_discoveries import ConversationDiscoveries
from src.application.tools.save_discovery_tool import SaveDiscoveryTool
from src.application.tools.seen_sources import SeenSources
from src.application.tools.suggest_improvement_tool import SuggestImprovementTool
from src.application.tools.web_search_tool import WebSearchTool
from src.domain.attention import Attention
from src.domain.discovery import Discovery
from src.domain.language_model import LanguageModel, LanguageModelError
from src.domain.text_embedding import TextEmbedder
from src.domain.tool import Tool
from src.evals.agent_run import AgentRun, GradedRun, RunOutcome, check_run
from src.evals.agent_scenarios import AgentScenario
from src.evals.agent_trace import RecordingLanguageModel, RecordingTool, RunTrace
from src.evals.faithfulness_judge import FaithfulnessJudge, FaithfulnessVerdict, JudgeError
from src.evals.retrieval_eval import EVAL_DATE
from src.evals.scripted_world import (
    FixedMemory,
    InMemoryDiscoveries,
    InMemorySearchHistory,
    InMemorySuggestions,
    ScriptedWebSearcher,
)

ATTENTION_CAPACITY = 5

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CapybaraPrompts:
    """The prompt files of the live capybara, loaded once by the caller."""

    system: str
    tool_result_reminder: str
    tool_result_reminders: dict[str, str]
    suggestion_invitation: str
    cycle_invitation: str
    known_discoveries: str
    noticed_things: str
    related_discoveries: str
    known_suggestions: str


@dataclass(frozen=True)
class AgentEvalSetup:
    language_model: LanguageModel
    embedder: TextEmbedder
    prompts: CapybaraPrompts
    max_steps: int
    max_remembered_discoveries: int
    recall_min_similarity: float
    suggestion_repeat_min_similarity: float
    recovered_tool_calls: Callable[[], int]
    """How many tool calls the model has written as text so far (read before and after)."""


@dataclass
class _ScenarioWorld:
    """Everything one run reads from and writes to, created fresh for every run."""

    discoveries: InMemoryDiscoveries
    suggestions: InMemorySuggestions
    tools: list[Tool]


def run_scenario(scenario: AgentScenario, setup: AgentEvalSetup) -> AgentRun:
    trace = RunTrace()
    world = _build_world(scenario, setup)
    conversation = Conversation(
        RecordingLanguageModel(setup.language_model, trace),
        setup.prompts.system,
        tools=[RecordingTool(tool, trace) for tool in world.tools],
        max_steps=setup.max_steps,
        tool_result_reminder=setup.prompts.tool_result_reminder,
        tool_result_reminders=setup.prompts.tool_result_reminders,
    )
    inner_voice = _build_inner_voice(scenario, setup, world)
    recovered_before = setup.recovered_tool_calls()
    outcome, final_answer = _talk(conversation, inner_voice.compose())
    return AgentRun(
        scenario=scenario.name,
        outcome=outcome,
        final_answer=final_answer,
        trace=trace,
        saved_discoveries=tuple(world.discoveries.saved),
        new_suggestions=tuple(world.suggestions.new_suggestions),
        recovered_tool_calls=setup.recovered_tool_calls() - recovered_before,
    )


def _talk(conversation: Conversation, inner_voice: str) -> tuple[RunOutcome, str]:
    """A failed run is a result too: it is counted, not allowed to stop the whole eval."""
    try:
        return RunOutcome.ANSWERED, conversation.send(inner_voice)
    except StepLimitReachedError:
        return RunOutcome.STEP_LIMIT, ""
    except LanguageModelError as error:
        return RunOutcome.MODEL_ERROR, str(error)


def _build_world(scenario: AgentScenario, setup: AgentEvalSetup) -> _ScenarioWorld:
    discoveries = InMemoryDiscoveries([known.headline() for known in scenario.known_discoveries])
    suggestions = InMemorySuggestions([])
    seen_sources = SeenSources()
    saved_discoveries = ConversationDiscoveries()
    web_search = WebSearchTool(
        ScriptedWebSearcher([page.search_result() for page in scenario.pages]),
        seen_sources=seen_sources,
        search_history=InMemorySearchHistory(scenario.earlier_searches, EVAL_DATE),
    )
    save_discovery = SaveDiscoveryTool(
        discoveries,
        seen_sources,
        illustrate=_no_drawing,
        saved_discoveries=saved_discoveries,
        follow_up=setup.prompts.suggestion_invitation,
    )
    suggest_improvement = SuggestImprovementTool(
        suggestions,
        RepeatedSuggestions(suggestions, setup.embedder, setup.suggestion_repeat_min_similarity),
        saved_discoveries,
    )
    return _ScenarioWorld(
        discoveries, suggestions, [web_search, save_discovery, suggest_improvement]
    )


def _build_inner_voice(
    scenario: AgentScenario, setup: AgentEvalSetup, world: _ScenarioWorld
) -> InnerVoice:
    attention = AttentionInbox(Attention(ATTENTION_CAPACITY, rest_seconds=0.0))
    for thing in scenario.noticed:
        attention.notice(thing.thing_id, thing.description)
    related_memory = FixedMemory([known.discovery() for known in scenario.related_discoveries])
    prompts = setup.prompts
    return InnerVoice(
        invitation=prompts.cycle_invitation,
        catalog=world.discoveries,
        memory_template=prompts.known_discoveries,
        max_remembered_discoveries=setup.max_remembered_discoveries,
        attention=attention,
        noticed_template=prompts.noticed_things,
        related=RelatedDiscoveries(related_memory, setup.recall_min_similarity),
        related_template=prompts.related_discoveries,
        suggestions=world.suggestions,
        suggestions_template=prompts.known_suggestions,
    )


def _no_drawing(discovery: Discovery) -> PinnedDrawing | None:
    """The chalkboard is left out of the eval: drawing choices are not what is measured here."""
    return None


def grade_run(run: AgentRun, scenario: AgentScenario, judge: FaithfulnessJudge) -> GradedRun:
    """Checks the run, then asks the judge about every discovery she saved in it.

    A judge that fails on one discovery leaves that discovery ungraded (logged).
    """
    verdicts: list[FaithfulnessVerdict] = []
    for discovery in run.saved_discoveries:
        try:
            verdicts.append(judge.judge(discovery, run.evidence))
        except (JudgeError, LanguageModelError) as error:
            logger.warning("Could not judge '%s': %s", discovery.title, error)
    return GradedRun(run, check_run(run, scenario.expect), verdicts)
