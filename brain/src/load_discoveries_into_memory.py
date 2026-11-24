"""Puts the discoveries already in the discoveries folder into the long-term memory.

Run once after setting up the memory (or any time: it never duplicates anything):
    cd brain
    python -m src.load_discoveries_into_memory
"""

import sys

import httpx

from src.application.backfill_memory import BackfillMemory, BackfillReport
from src.domain.discovery_memory import DiscoveryMemoryError
from src.infrastructure.logging_setup import configure_logging
from src.infrastructure.markdown_discovery_repository import MarkdownDiscoveryRepository
from src.infrastructure.settings import Settings
from src.long_term_memory import open_long_term_memory

MEMORY_OFFLINE_HINT = (
    "Confira se o banco está ligado (docker compose --env-file brain/.env up -d) "
    "e se o Ollama está rodando com o nomic-embed-text. Pode rodar de novo: nada é duplicado."
)


def print_report(report: BackfillReport) -> None:
    print(f"{len(report.remembered)} descoberta(s) lembrada(s).")
    if not report.skipped:
        return
    print(f"{len(report.skipped)} arquivo(s) pulado(s):")
    for skipped_file in report.skipped:
        print(f"  - {skipped_file.file_name}: {skipped_file.reason}")


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_file, settings.log_level)
    archive = MarkdownDiscoveryRepository(settings.discoveries_dir)
    print(f"Lendo as descobertas de {settings.discoveries_dir}...", flush=True)
    with (
        httpx.Client(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_seconds,
        ) as http_client,
        open_long_term_memory(settings, http_client) as memory,
    ):
        try:
            report = BackfillMemory(archive, memory).execute()
        except DiscoveryMemoryError as error:
            print(f"Não consegui guardar na memória: {error}", file=sys.stderr)
            print(MEMORY_OFFLINE_HINT, file=sys.stderr)
            raise SystemExit(1) from error
    print_report(report)


if __name__ == "__main__":
    main()
