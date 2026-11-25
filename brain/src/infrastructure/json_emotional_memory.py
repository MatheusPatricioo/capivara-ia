import os
from pathlib import Path

from pydantic import BaseModel, ValidationError

from src.domain.feelings.appraisal import EventKind, Familiarity
from src.domain.feelings.baseline import Baseline
from src.domain.feelings.bond import Bond
from src.domain.feelings.emotion import Emotion, EmotionalState
from src.domain.feelings.emotional_life import EmotionalSnapshot
from src.domain.feelings.emotional_memory import EmotionalMemoryError
from src.domain.feelings.ladders import LadderPosition
from src.domain.feelings.mood import Mood
from src.domain.feelings.needs import Need, Needs

TEMPORARY_SUFFIX = ".tmp"


class _LadderPositionData(BaseModel):
    rung_index: int
    jitter: float


class _SnapshotData(BaseModel):
    """The JSON shape of her emotional life. Readable on purpose: open it to watch her."""

    emotions: dict[Emotion, float]
    needs: dict[Need, float]
    mood_valence: float
    mood_arousal: float
    baseline_shift: float
    trust: float
    last_updated_at: float
    ladder_positions: dict[Need, _LadderPositionData]
    familiarity: dict[EventKind, float]
    success_streak: int
    failure_streak: int
    pending_wishes: int
    last_talked_at: float | None
    day_number: int
    day_spirit: float


class JsonEmotionalMemory:
    """Keeps her emotional life in one JSON file.

    The chat and the live capybara run in different processes and share this file, so
    every write goes to a temporary file first and then replaces the real one in a single
    step: a reader never sees half a file.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> EmotionalSnapshot | None:
        if not self._path.exists():
            return None
        try:
            data = _SnapshotData.model_validate_json(self._path.read_text(encoding="utf-8"))
            return _snapshot_from(data)
        except (OSError, ValidationError, ValueError) as error:
            raise EmotionalMemoryError(f"could not read {self._path.name}: {error}") from error

    def save(self, snapshot: EmotionalSnapshot) -> None:
        temporary = self._path.with_name(self._path.name + TEMPORARY_SUFFIX)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(_data_from(snapshot).model_dump_json(indent=2), encoding="utf-8")
            os.replace(temporary, self._path)
        except OSError as error:
            raise EmotionalMemoryError(f"could not write {self._path.name}: {error}") from error


def _data_from(snapshot: EmotionalSnapshot) -> _SnapshotData:
    return _SnapshotData(
        emotions={
            emotion: round(intensity, 4)
            for emotion, intensity in snapshot.emotions.intensities.items()
        },
        needs={need: round(level, 4) for need, level in snapshot.needs.levels.items()},
        mood_valence=snapshot.mood.valence,
        mood_arousal=snapshot.mood.arousal,
        baseline_shift=snapshot.baseline.shift,
        trust=snapshot.bond.trust,
        last_updated_at=snapshot.last_updated_at,
        ladder_positions={
            need: _LadderPositionData(rung_index=position.rung_index, jitter=position.jitter)
            for need, position in snapshot.ladder_positions.items()
        },
        familiarity=dict(snapshot.familiarity.counts),
        success_streak=snapshot.success_streak,
        failure_streak=snapshot.failure_streak,
        pending_wishes=snapshot.pending_wishes,
        last_talked_at=snapshot.last_talked_at,
        day_number=snapshot.day_number,
        day_spirit=snapshot.day_spirit,
    )


def _snapshot_from(data: _SnapshotData) -> EmotionalSnapshot:
    """The domain classes validate the ranges again: a hand-edited file cannot break her."""
    return EmotionalSnapshot(
        emotions=EmotionalState(data.emotions),
        needs=Needs(data.needs),
        mood=Mood(valence=data.mood_valence, arousal=data.mood_arousal),
        baseline=Baseline(data.baseline_shift),
        bond=Bond(trust=data.trust),
        last_updated_at=data.last_updated_at,
        ladder_positions={
            need: LadderPosition(position.rung_index, position.jitter)
            for need, position in data.ladder_positions.items()
        },
        familiarity=Familiarity(data.familiarity),
        success_streak=data.success_streak,
        failure_streak=data.failure_streak,
        pending_wishes=data.pending_wishes,
        last_talked_at=data.last_talked_at,
        day_number=data.day_number,
        day_spirit=data.day_spirit,
    )
