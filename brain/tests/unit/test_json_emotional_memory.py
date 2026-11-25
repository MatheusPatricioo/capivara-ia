import random
from pathlib import Path

import pytest

from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.feelings.emotional_life import EmotionalLife, EmotionalSnapshot
from src.domain.feelings.emotional_memory import EmotionalMemoryError
from src.infrastructure.json_emotional_memory import JsonEmotionalMemory

BORN_AT = 1_800_000_000.0
TWO_DAYS_LATER = BORN_AT + 2 * 86400.0


@pytest.fixture
def lived_snapshot() -> EmotionalSnapshot:
    """A life with something in every field: talked, waited, failed, slept."""
    life = EmotionalLife(EmotionalLife.newborn(BORN_AT), rng=random.Random(3))
    life.experience(EmotionalEvent(EventKind.TALKED_WITH_MATHEUS), BORN_AT)
    life.experience(EmotionalEvent(EventKind.WISH_MADE), BORN_AT)
    life.experience(EmotionalEvent(EventKind.SEARCH_FOUND_NOTHING), TWO_DAYS_LATER)
    return life.snapshot()


@pytest.fixture
def memory(tmp_path: Path) -> JsonEmotionalMemory:
    return JsonEmotionalMemory(tmp_path / "feelings.json")


def test_without_a_file_she_has_no_emotional_life_yet(memory: JsonEmotionalMemory) -> None:
    assert memory.load() is None


def test_what_is_saved_comes_back_the_same(
    memory: JsonEmotionalMemory, lived_snapshot: EmotionalSnapshot
) -> None:
    memory.save(lived_snapshot)

    restored = memory.load()

    assert restored is not None
    assert restored.ladder_positions == lived_snapshot.ladder_positions
    assert restored.last_talked_at == lived_snapshot.last_talked_at
    assert restored.emotions.intensities == pytest.approx(
        dict(lived_snapshot.emotions.intensities), abs=0.0001
    )


def test_saving_leaves_no_temporary_file_behind(
    memory: JsonEmotionalMemory, lived_snapshot: EmotionalSnapshot, tmp_path: Path
) -> None:
    memory.save(lived_snapshot)

    assert [path.name for path in tmp_path.iterdir()] == ["feelings.json"]


def test_saving_creates_the_folder(tmp_path: Path, lived_snapshot: EmotionalSnapshot) -> None:
    memory = JsonEmotionalMemory(tmp_path / "new" / "feelings.json")

    memory.save(lived_snapshot)

    assert (tmp_path / "new" / "feelings.json").exists()


def test_a_broken_file_is_an_emotional_memory_error(
    memory: JsonEmotionalMemory, tmp_path: Path
) -> None:
    (tmp_path / "feelings.json").write_text("{ not json", encoding="utf-8")

    with pytest.raises(EmotionalMemoryError, match="feelings.json"):
        memory.load()


def test_a_hand_edited_intensity_out_of_range_is_refused(
    memory: JsonEmotionalMemory, lived_snapshot: EmotionalSnapshot, tmp_path: Path
) -> None:
    memory.save(lived_snapshot)
    feelings_file = tmp_path / "feelings.json"
    feelings_file.write_text(
        feelings_file.read_text(encoding="utf-8").replace('"trust": ', '"trust": 9'),
        encoding="utf-8",
    )

    with pytest.raises(EmotionalMemoryError):
        memory.load()
