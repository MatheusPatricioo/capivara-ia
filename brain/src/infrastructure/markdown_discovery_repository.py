from datetime import date
from pathlib import Path

from src.domain.discovery import Discovery, DiscoveryHeadline, DiscoveryStorageError
from src.infrastructure.markdown_notes import first_value_after, section_lines
from src.infrastructure.safe_file_names import free_dated_file_path, is_inside

FILE_EXTENSION = ".md"
# The Markdown layout, shared by writing and reading so both always agree.
TITLE_PREFIX = "# "
DATE_PREFIX = "- **Data:** "
TOPIC_PREFIX = "- **Tema:** "
SUMMARY_HEADING = "## O que eu descobri"
SOURCES_HEADING = "## Fontes"
LIST_ITEM_PREFIX = "- "
NO_SOURCES_LINE = "- (nenhuma)"


def _from_markdown(file_name: str, lines: list[str]) -> Discovery:
    """Reads back a discovery written by _to_markdown; the summary may span paragraphs."""
    title = first_value_after(TITLE_PREFIX, lines)
    if not title:
        raise DiscoveryStorageError(f"{file_name} is not a discovery: it has no title")
    date_text = first_value_after(DATE_PREFIX, lines)
    try:
        discovered_on = date.fromisoformat(date_text)
    except ValueError as error:
        raise DiscoveryStorageError(
            f"{file_name} has no valid date (found '{date_text}')"
        ) from error
    summary = "\n".join(section_lines(SUMMARY_HEADING, lines)).strip()
    if not summary:
        raise DiscoveryStorageError(f"{file_name} has no summary")
    return Discovery(
        title=title,
        topic=first_value_after(TOPIC_PREFIX, lines),
        summary=summary,
        sources=_sources(section_lines(SOURCES_HEADING, lines)),
        discovered_on=discovered_on,
    )


def _sources(source_lines: list[str]) -> tuple[str, ...]:
    return tuple(
        line.removeprefix(LIST_ITEM_PREFIX).strip()
        for line in source_lines
        if line.startswith(LIST_ITEM_PREFIX) and line != NO_SOURCES_LINE
    )


class MarkdownDiscoveryRepository:
    """Saves each discovery as a Markdown file inside the discoveries folder."""

    def __init__(self, discoveries_dir: Path) -> None:
        self._discoveries_dir = discoveries_dir.resolve()

    def save(self, discovery: Discovery) -> str:
        try:
            self._discoveries_dir.mkdir(parents=True, exist_ok=True)
            file_path = free_dated_file_path(
                self._discoveries_dir, discovery.discovered_on, discovery.title, FILE_EXTENSION
            )
            self._ensure_inside_discoveries_dir(file_path)
            with file_path.open("x", encoding="utf-8") as discovery_file:
                discovery_file.write(self._to_markdown(discovery))
        except OSError as error:
            raise DiscoveryStorageError(f"could not save the discovery: {error}") from error
        return file_path.name

    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        """Reads title and topic back from the newest files (names start with the date).

        Markdown files without a title line are skipped, so notes dropped into the
        folder by hand do not break anything.
        """
        headlines: list[DiscoveryHeadline] = []
        for discovery_file in reversed(self._discovery_files()):
            if len(headlines) == limit:
                break
            headline = self._read_headline(discovery_file)
            if headline is not None:
                headlines.append(headline)
        return headlines

    def saved_file_names(self) -> list[str]:
        """Every Markdown file in the folder (not in subfolders), the oldest first.

        Names start with the date, so sorting by name sorts by date.
        """
        return [discovery_file.name for discovery_file in self._discovery_files()]

    def read(self, file_name: str) -> Discovery:
        file_path = self._discoveries_dir / file_name
        self._ensure_inside_discoveries_dir(file_path)
        return _from_markdown(file_name, self._read_lines(file_path))

    def _discovery_files(self) -> list[Path]:
        if not self._discoveries_dir.is_dir():
            return []
        return sorted(
            self._discoveries_dir.glob(f"*{FILE_EXTENSION}"),
            key=lambda discovery_file: discovery_file.name,
        )

    @staticmethod
    def _read_lines(discovery_file: Path) -> list[str]:
        try:
            return discovery_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise DiscoveryStorageError(
                f"could not read the discovery {discovery_file.name}: {error}"
            ) from error

    def _read_headline(self, discovery_file: Path) -> DiscoveryHeadline | None:
        lines = self._read_lines(discovery_file)
        title = first_value_after(TITLE_PREFIX, lines)
        if not title:
            return None
        return DiscoveryHeadline(title=title, topic=first_value_after(TOPIC_PREFIX, lines))

    def _ensure_inside_discoveries_dir(self, file_path: Path) -> None:
        if not is_inside(self._discoveries_dir, file_path):
            raise DiscoveryStorageError(
                f"refusing to touch a file outside the discoveries folder: {file_path}"
            )

    @staticmethod
    def _to_markdown(discovery: Discovery) -> str:
        source_lines = "\n".join(f"{LIST_ITEM_PREFIX}{source}" for source in discovery.sources)
        return (
            f"{TITLE_PREFIX}{discovery.title}\n\n"
            f"{DATE_PREFIX}{discovery.discovered_on.isoformat()}\n"
            f"{TOPIC_PREFIX}{discovery.topic}\n\n"
            f"{SUMMARY_HEADING}\n\n"
            f"{discovery.summary}\n\n"
            f"{SOURCES_HEADING}\n\n"
            f"{source_lines or NO_SOURCES_LINE}\n"
        )
