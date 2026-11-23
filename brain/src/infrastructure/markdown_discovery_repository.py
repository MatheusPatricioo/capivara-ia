import re
import unicodedata
from pathlib import Path

from src.domain.discovery import Discovery, DiscoveryHeadline, DiscoveryStorageError

FILE_EXTENSION = ".md"
TITLE_PREFIX = "# "
TOPIC_PREFIX = "- **Tema:** "
FALLBACK_SLUG = "descoberta"
MAX_SLUG_LENGTH = 60
NON_SLUG_CHARACTERS = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Turns any text into lowercase ASCII words joined by hyphens, safe for a file name."""
    without_accents = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    slug = NON_SLUG_CHARACTERS.sub("-", without_accents.lower()).strip("-")
    shortened_slug = slug[:MAX_SLUG_LENGTH].rstrip("-")
    return shortened_slug or FALLBACK_SLUG


def _first_value_after(prefix: str, lines: list[str]) -> str:
    """Returns what follows the prefix on the first line that starts with it, or ''."""
    for line in lines:
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


class MarkdownDiscoveryRepository:
    """Saves each discovery as a Markdown file inside the discoveries folder."""

    def __init__(self, discoveries_dir: Path) -> None:
        self._discoveries_dir = discoveries_dir.resolve()

    def save(self, discovery: Discovery) -> str:
        try:
            self._discoveries_dir.mkdir(parents=True, exist_ok=True)
            file_path = self._free_file_path(discovery)
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
        if not self._discoveries_dir.is_dir():
            return []
        discovery_files = sorted(
            self._discoveries_dir.glob(f"*{FILE_EXTENSION}"),
            key=lambda discovery_file: discovery_file.name,
            reverse=True,
        )
        headlines: list[DiscoveryHeadline] = []
        for discovery_file in discovery_files:
            if len(headlines) == limit:
                break
            headline = self._read_headline(discovery_file)
            if headline is not None:
                headlines.append(headline)
        return headlines

    @staticmethod
    def _read_headline(discovery_file: Path) -> DiscoveryHeadline | None:
        try:
            lines = discovery_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise DiscoveryStorageError(
                f"could not read the discovery {discovery_file.name}: {error}"
            ) from error
        title = _first_value_after(TITLE_PREFIX, lines)
        if not title:
            return None
        return DiscoveryHeadline(title=title, topic=_first_value_after(TOPIC_PREFIX, lines))

    def _free_file_path(self, discovery: Discovery) -> Path:
        """Builds date + slug, adding -2, -3... so an existing file is never overwritten."""
        base_name = f"{discovery.discovered_on.isoformat()}-{slugify(discovery.title)}"
        file_path = self._discoveries_dir / f"{base_name}{FILE_EXTENSION}"
        copy_number = 2
        while file_path.exists():
            file_path = self._discoveries_dir / f"{base_name}-{copy_number}{FILE_EXTENSION}"
            copy_number += 1
        return file_path

    def _ensure_inside_discoveries_dir(self, file_path: Path) -> None:
        """Defense in depth: the slug already blocks traversal, this double-checks it."""
        if not file_path.resolve().is_relative_to(self._discoveries_dir):
            raise DiscoveryStorageError(
                f"refusing to write outside the discoveries folder: {file_path}"
            )

    @staticmethod
    def _to_markdown(discovery: Discovery) -> str:
        source_lines = "\n".join(f"- {source}" for source in discovery.sources)
        return (
            f"{TITLE_PREFIX}{discovery.title}\n\n"
            f"- **Data:** {discovery.discovered_on.isoformat()}\n"
            f"{TOPIC_PREFIX}{discovery.topic}\n\n"
            f"## O que eu descobri\n\n"
            f"{discovery.summary}\n\n"
            f"## Fontes\n\n"
            f"{source_lines or '- (nenhuma)'}\n"
        )
