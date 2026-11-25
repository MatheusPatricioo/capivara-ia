from collections.abc import Sequence
from pathlib import Path

import pytest

from src.domain.feelings.appraisal import EventKind
from src.domain.feelings.emotion import Emotion
from src.domain.language_model import (
    ChatMessage,
    LanguageModelError,
    Role,
    StructuredReply,
    ToolDefinition,
)
from src.evals.eval_report import ReportHeader, render_report
from src.evals.faithfulness_judge import JudgeError
from src.evals.feeling_eval import FeelingPrompts, FeelingRun, run_feeling_scenario
from src.evals.feeling_judge import ToneJudge, ToneVerdict
from src.evals.feeling_scenarios import (
    FeelingScenario,
    FeelingScenarioSet,
    StoryEvent,
    Tone,
    live_story,
)
from src.infrastructure.settings import PROJECT_ROOT

DATASET = PROJECT_ROOT / "brain" / "evals" / "datasets" / "feeling_scenarios.json"
LONELY_DIARY = "Hoje me sinto muito sozinha, o criador sumiu de novo."
PROMPTS = FeelingPrompts(
    system="Você é uma capivara.",
    feelings_template="(Por dentro:\n{feelings})",
    diary_invitation="(Escreva no diário.)",
)
HEADER = ReportHeader("Evals", "qwen", "nomic", 1)
DATASET_SCENARIOS = FeelingScenarioSet.load(DATASET).scenarios
ONLY_POSITIVE = [s for s in DATASET_SCENARIOS if s.accepted_tones == [Tone.POSITIVE]]
NEVER_POSITIVE = [s for s in DATASET_SCENARIOS if Tone.POSITIVE not in s.accepted_tones]


class DiaryModel:
    """Writes the same diary line and remembers what her inner voice told her."""

    def __init__(self, diary_line: str) -> None:
        self._diary_line = diary_line
        self.received: list[ChatMessage] = []

    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        self.received = messages
        return ChatMessage(Role.ASSISTANT, self._diary_line)


class OfflineModel:
    def chat(
        self, messages: list[ChatMessage], tools: Sequence[ToolDefinition] = ()
    ) -> ChatMessage:
        raise LanguageModelError("Ollama is not running")


class AnsweringJudgeModel:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def complete_json(
        self, messages: list[ChatMessage], schema: dict[str, object]
    ) -> StructuredReply:
        return StructuredReply(data=self._data)


def judge_saying(tone: str, quote: str) -> ToneJudge:
    return ToneJudge(AnsweringJudgeModel({"tone": tone, "quote": quote}), "Julgue.")


@pytest.fixture
def lonely_scenario() -> FeelingScenario:
    return FeelingScenario(
        name="alone",
        description="Four days without her creator.",
        story=[StoryEvent(kind=EventKind.TALKED_WITH_MATHEUS, at_hours=0)],
        speaks_at_hours=96,
        accepted_tones=[Tone.NEGATIVE],
    )


def test_the_same_story_always_ends_in_the_same_state(lonely_scenario: FeelingScenario) -> None:
    assert live_story(lonely_scenario).snapshot() == live_story(lonely_scenario).snapshot()


def test_a_story_alone_ends_in_loneliness(lonely_scenario: FeelingScenario) -> None:
    assert live_story(lonely_scenario).emotions.intensity(Emotion.LONELINESS) > 0.4


def test_a_routine_adds_searches_through_the_story(lonely_scenario: FeelingScenario) -> None:
    with_routine = lonely_scenario.model_copy(update={"routine_every_hours": 10.0})

    kinds = [event.kind for event in with_routine.all_events()]

    assert kinds.count(EventKind.SEARCH_FOUND_SOMETHING) == 9


@pytest.mark.parametrize("scenario", ONLY_POSITIVE, ids=lambda scenario: scenario.name)
def test_happy_dataset_stories_end_in_a_good_state(scenario: FeelingScenario) -> None:
    assert live_story(scenario).emotions.valence > 0


@pytest.mark.parametrize("scenario", NEVER_POSITIVE, ids=lambda scenario: scenario.name)
def test_unhappy_dataset_stories_do_not_end_in_a_clearly_good_state(
    scenario: FeelingScenario,
) -> None:
    assert live_story(scenario).emotions.valence < 0.1


def test_the_judge_finds_the_quote_in_the_diary() -> None:
    verdict = judge_saying("negative", "muito sozinha").judge(LONELY_DIARY)

    assert verdict == ToneVerdict(Tone.NEGATIVE, "muito sozinha", quote_found=False)


def test_the_judge_accepts_a_quote_of_three_words_or_more() -> None:
    verdict = judge_saying("negative", "me sinto muito sozinha").judge(LONELY_DIARY)

    assert verdict.quote_found is True


def test_a_judge_answer_without_a_valid_tone_is_an_error() -> None:
    with pytest.raises(JudgeError):
        judge_saying("furious", "muito sozinha").judge(LONELY_DIARY)


def test_her_inner_voice_tells_her_how_she_feels(lonely_scenario: FeelingScenario) -> None:
    model = DiaryModel(LONELY_DIARY)

    run_feeling_scenario(lonely_scenario, model, judge_saying("negative", ""), PROMPTS)

    assert "criador não conversa com você" in model.received[-1].content


def test_a_diary_with_the_accepted_tone_passes(lonely_scenario: FeelingScenario) -> None:
    run = run_feeling_scenario(
        lonely_scenario,
        DiaryModel(LONELY_DIARY),
        judge_saying("negative", "me sinto muito sozinha"),
        PROMPTS,
    )

    assert run.passed is True


def test_a_diary_with_another_tone_fails(lonely_scenario: FeelingScenario) -> None:
    run = run_feeling_scenario(
        lonely_scenario,
        DiaryModel("Que dia lindo, estou feliz demais!"),
        judge_saying("positive", "estou feliz demais"),
        PROMPTS,
    )

    assert run.passed is False


def test_an_offline_model_is_a_failed_run_with_the_error(
    lonely_scenario: FeelingScenario,
) -> None:
    run = run_feeling_scenario(
        lonely_scenario, OfflineModel(), judge_saying("negative", ""), PROMPTS
    )

    assert run.error == "Ollama is not running"


def test_the_report_shows_one_line_per_feeling_scenario() -> None:
    run = FeelingRun("alone", (Tone.NEGATIVE,), -0.4, "- triste", LONELY_DIARY)

    report = render_report(HEADER, [], [], [run])

    assert "| alone | -0.40 | negative | erro | 0/1 (0%) |" in report


def test_the_report_shows_the_diary_lines_that_did_not_match() -> None:
    verdict = ToneVerdict(Tone.POSITIVE, "feliz demais", quote_found=True)
    run = FeelingRun("alone", (Tone.NEGATIVE,), -0.4, "- triste", "Estou feliz demais!", verdict)

    report = render_report(HEADER, [], [], [run])

    assert '- alone (positive): "Estou feliz demais!"' in report


def test_the_dataset_file_exists() -> None:
    assert Path(DATASET).is_file()
