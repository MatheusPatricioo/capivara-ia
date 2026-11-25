"""Feeling eval scenarios: a stretch of her life, lived through the real emotional rules.

Each scenario is a story (events at given hours). The story is lived awake, in small
steps, with a fixed seed, so the same scenario always ends in the same emotional state.
"""

import random
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.emotional_life import SECONDS_PER_HOUR, EmotionalLife

STORY_START = 1_800_000_000.0
AWAKE_STEP_HOURS = 0.5
STORY_SEED = 7
COMFORT_EVERY_ROUTINES = 3


class Tone(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class StoryEvent(BaseModel):
    kind: EventKind
    at_hours: float = Field(ge=0)
    waited_hours: float = Field(default=0.0, ge=0)


class FeelingScenario(BaseModel):
    name: str
    description: str
    story: list[StoryEvent]
    speaks_at_hours: float = Field(ge=0)
    """When she writes in her diary, after the story."""
    accepted_tones: list[Tone] = Field(min_length=1)
    routine_every_hours: float | None = Field(default=None, gt=0)
    """Her ordinary life in long stories: a search that finds something this often, and a
    visit to a comfort place every COMFORT_EVERY_ROUTINES of them, like the live loop."""

    def all_events(self) -> list[StoryEvent]:
        """The story plus her routine, in order of time."""
        return sorted([*self.story, *self._routine()], key=lambda story_event: story_event.at_hours)

    def _routine(self) -> list[StoryEvent]:
        if self.routine_every_hours is None:
            return []
        events: list[StoryEvent] = []
        count = 1
        while count * self.routine_every_hours < self.speaks_at_hours:
            at_hours = count * self.routine_every_hours
            events.append(StoryEvent(kind=EventKind.SEARCH_FOUND_SOMETHING, at_hours=at_hours))
            if count % COMFORT_EVERY_ROUTINES == 0:
                events.append(StoryEvent(kind=EventKind.VISITED_COMFORT_PLACE, at_hours=at_hours))
            count += 1
        return events


class FeelingScenarioSet(BaseModel):
    scenarios: list[FeelingScenario]

    @classmethod
    def load(cls, path: Path) -> "FeelingScenarioSet":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


def story_time(hours: float) -> float:
    return STORY_START + hours * SECONDS_PER_HOUR


def live_story(scenario: FeelingScenario, seed: int = STORY_SEED) -> EmotionalLife:
    """Lives the story awake, the way the live loop checks on her every few minutes."""
    life = EmotionalLife(EmotionalLife.newborn(STORY_START), rng=random.Random(seed))
    hours = 0.0
    for event in scenario.all_events():
        hours = _stay_awake(life, hours, event.at_hours)
        life.experience(EmotionalEvent(event.kind, event.waited_hours), story_time(hours))
    _stay_awake(life, hours, scenario.speaks_at_hours)
    return life


def _stay_awake(life: EmotionalLife, from_hours: float, to_hours: float) -> float:
    hours = from_hours
    while hours < to_hours:
        hours = min(hours + AWAKE_STEP_HOURS, to_hours)
        life.advance(story_time(hours))
    return hours
