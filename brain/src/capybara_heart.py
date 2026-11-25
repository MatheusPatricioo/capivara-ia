"""Builds the capybara's heart. Shared by the chat, the live capybara and the scripts."""

from src.application.heart import Heart
from src.infrastructure.json_emotional_memory import JsonEmotionalMemory
from src.infrastructure.settings import Settings

FEELINGS_FILE_NAME = "feelings.json"


def build_heart(settings: Settings) -> Heart | None:
    """None when FEELINGS_ENABLED is off: then she behaves as before the feelings existed."""
    if not settings.feelings_enabled:
        return None
    return Heart(
        JsonEmotionalMemory(settings.discoveries_dir / FEELINGS_FILE_NAME),
        settings.temperament(),
        settings.need_rhythm(),
    )
