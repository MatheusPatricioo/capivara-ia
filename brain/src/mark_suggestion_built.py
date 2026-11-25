"""Marks one of the capybara's suggestions as built, after you build it in the Godot world.

    cd brain
    python -m src.mark_suggestion_built                       # lists the suggestions waiting
    python -m src.mark_suggestion_built <file>                # marks <file> as built
    python -m src.mark_suggestion_built <file> --thing-id water_lilies

--thing-id is the thing_id of the Observable you placed in the world for it: when she walks
by it, she recognizes it as the thing she asked for. Changing the "Situação" line of the
file by hand to "construída" works too, but then she does not feel her wish come true.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import date

from src.application.heart import Heart
from src.capybara_heart import build_heart
from src.domain.feelings.appraisal import EmotionalEvent, EventKind
from src.domain.world_suggestion import (
    InvalidSuggestionError,
    SuggestionStorageError,
    WorldSuggestion,
)
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.settings import Settings

SUCCESS = 0
FAILURE = 1
HOURS_PER_DAY = 24.0


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.mark_suggestion_built",
        description="Marca uma sugestão da capivara como construída no mundo.",
    )
    parser.add_argument(
        "file_name",
        nargs="?",
        help="arquivo da sugestão em sugestoes/ (sem ele, lista as que estão esperando)",
    )
    parser.add_argument(
        "--thing-id",
        default="",
        help="thing_id do Observable que você colocou no mundo para ela reconhecer",
    )
    return parser.parse_args(arguments)


def list_waiting(repository: MarkdownSuggestionRepository) -> int:
    waiting = [saved for saved in repository.saved_suggestions() if not saved.suggestion.is_built]
    if not waiting:
        print("Nenhuma sugestão esperando.")
        return SUCCESS
    print("Sugestões esperando:")
    for saved in waiting:
        print(f"  {saved.file_name}  ({saved.suggestion.request})")
    return SUCCESS


def _ignore_built(suggestion: WorldSuggestion) -> None:
    pass


def mark_built(
    repository: MarkdownSuggestionRepository,
    file_name: str,
    thing_id: str,
    on_built: Callable[[WorldSuggestion], None] = _ignore_built,
) -> int:
    try:
        saved = repository.mark_built(file_name, thing_id)
    except (SuggestionStorageError, InvalidSuggestionError) as error:
        print(f"Não consegui marcar a sugestão: {error}", file=sys.stderr)
        return FAILURE
    on_built(saved.suggestion)
    print(f'Marcada como construída: "{saved.suggestion.request}" ({saved.file_name}).')
    if saved.suggestion.world_thing_id:
        print(f"Ela vai reconhecer o pedido quando passar por {saved.suggestion.world_thing_id}.")
    return SUCCESS


def run(
    arguments: Sequence[str],
    repository: MarkdownSuggestionRepository,
    on_built: Callable[[WorldSuggestion], None] = _ignore_built,
) -> int:
    parsed = parse_arguments(arguments)
    if parsed.file_name is None:
        return list_waiting(repository)
    return mark_built(repository, parsed.file_name, parsed.thing_id, on_built)


def waited_hours(suggestion: WorldSuggestion, today: date) -> float:
    """How long she waited for it; only the day is known, so it counts whole days."""
    return max(0, (today - suggestion.suggested_on).days) * HOURS_PER_DAY


def granted_wish_listener(heart: Heart) -> Callable[[WorldSuggestion], None]:
    """She feels her wish come true: the longer she waited, the stronger it lands."""

    def feel_granted(suggestion: WorldSuggestion) -> None:
        heart.feel(EmotionalEvent(EventKind.WISH_GRANTED, waited_hours(suggestion, date.today())))

    return feel_granted


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    heart = build_heart(settings)
    on_built = granted_wish_listener(heart) if heart is not None else _ignore_built
    repository = MarkdownSuggestionRepository(settings.discoveries_dir)
    raise SystemExit(run(sys.argv[1:], repository, on_built))


if __name__ == "__main__":
    main()
