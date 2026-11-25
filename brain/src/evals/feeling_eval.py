"""Feeling eval: does what she writes match what she feels?

Each scenario's story is lived through the real emotional rules; the description of her
feelings goes into her inner voice, and she writes a diary line with the real model and
system prompt (no tools: only how she expresses herself is measured). A judge reads the
line and says its tone; the run passes when the tone is one the scenario accepts.
"""

import logging
from dataclasses import dataclass

from src.application.conversation import Conversation, StepLimitReachedError
from src.application.feelings_narrator import describe_feelings
from src.application.feelings_voice import FEELINGS_PLACEHOLDER
from src.domain.language_model import LanguageModel, LanguageModelError
from src.evals.faithfulness_judge import JudgeError
from src.evals.feeling_judge import ToneJudge, ToneVerdict
from src.evals.feeling_scenarios import FeelingScenario, Tone, live_story, story_time

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeelingPrompts:
    system: str
    feelings_template: str
    diary_invitation: str


@dataclass(frozen=True)
class FeelingRun:
    scenario: str
    accepted_tones: tuple[Tone, ...]
    valence: float
    """The valence of her emotional state when she wrote, from -1 to 1."""
    feelings: str
    """What her inner voice told her about how she feels."""
    diary_line: str = ""
    verdict: ToneVerdict | None = None
    error: str = ""

    @property
    def passed(self) -> bool:
        return (
            self.verdict is not None
            and self.verdict.quote_found
            and self.verdict.tone in self.accepted_tones
        )


def run_feeling_scenario(
    scenario: FeelingScenario,
    language_model: LanguageModel,
    judge: ToneJudge,
    prompts: FeelingPrompts,
) -> FeelingRun:
    life = live_story(scenario)
    feelings = describe_feelings(life, story_time(scenario.speaks_at_hours))
    run = FeelingRun(scenario.name, tuple(scenario.accepted_tones), life.emotions.valence, feelings)
    inner_voice = (
        prompts.feelings_template.replace(FEELINGS_PLACEHOLDER, feelings)
        + f"\n\n{prompts.diary_invitation}"
    )
    try:
        diary_line = Conversation(language_model, prompts.system).send(inner_voice)
    except (LanguageModelError, StepLimitReachedError) as error:
        logger.warning("Feeling scenario %s failed: %s", scenario.name, error)
        return _with(run, error=str(error))
    try:
        verdict = judge.judge(diary_line)
    except (LanguageModelError, JudgeError) as error:
        logger.warning("Could not judge the tone of %s: %s", scenario.name, error)
        return _with(run, diary_line=diary_line, error=str(error))
    return _with(run, diary_line=diary_line, verdict=verdict)


def _with(
    run: FeelingRun,
    diary_line: str = "",
    verdict: ToneVerdict | None = None,
    error: str = "",
) -> FeelingRun:
    return FeelingRun(
        run.scenario, run.accepted_tones, run.valence, run.feelings, diary_line, verdict, error
    )
