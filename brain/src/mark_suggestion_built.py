"""Marks one of the capybara's suggestions as built, after you build it in the Godot world.

    cd brain
    python -m src.mark_suggestion_built                       # lists the suggestions waiting
    python -m src.mark_suggestion_built <file>                # marks <file> as built
    python -m src.mark_suggestion_built <file> --thing-id water_lilies

--thing-id is the thing_id of the Observable you placed in the world for it: when she walks
by it, she recognizes it as the thing she asked for. Changing the "Situação" line of the
file by hand to "construída" works too.
"""

import argparse
import sys
from collections.abc import Sequence

from src.domain.world_suggestion import InvalidSuggestionError, SuggestionStorageError
from src.infrastructure.markdown_suggestion_repository import MarkdownSuggestionRepository
from src.infrastructure.settings import Settings

SUCCESS = 0
FAILURE = 1


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


def mark_built(repository: MarkdownSuggestionRepository, file_name: str, thing_id: str) -> int:
    try:
        saved = repository.mark_built(file_name, thing_id)
    except (SuggestionStorageError, InvalidSuggestionError) as error:
        print(f"Não consegui marcar a sugestão: {error}", file=sys.stderr)
        return FAILURE
    print(f'Marcada como construída: "{saved.suggestion.request}" ({saved.file_name}).')
    if saved.suggestion.world_thing_id:
        print(f"Ela vai reconhecer o pedido quando passar por {saved.suggestion.world_thing_id}.")
    return SUCCESS


def run(arguments: Sequence[str], repository: MarkdownSuggestionRepository) -> int:
    parsed = parse_arguments(arguments)
    if parsed.file_name is None:
        return list_waiting(repository)
    return mark_built(repository, parsed.file_name, parsed.thing_id)


def main() -> None:
    settings = Settings()
    raise SystemExit(run(sys.argv[1:], MarkdownSuggestionRepository(settings.discoveries_dir)))


if __name__ == "__main__":
    main()
