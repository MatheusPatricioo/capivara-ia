"""File names for what the capybara saves: readable, never overwriting, never escaping a folder.

Shared by every repository that writes into the discoveries folder (notes, drawings,
suggestions). Each repository still raises its own storage error, so this module only
answers questions and never raises.
"""

import re
import unicodedata
from datetime import date
from pathlib import Path

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


def free_dated_file_path(folder: Path, day: date, title: str, extension: str) -> Path:
    """Builds date + slug, adding -2, -3... so an existing file is never overwritten.

    Names start with the date, so sorting them by name sorts them by date.
    """
    base_name = f"{day.isoformat()}-{slugify(title)}"
    file_path = folder / f"{base_name}{extension}"
    copy_number = 2
    while file_path.exists():
        file_path = folder / f"{base_name}-{copy_number}{extension}"
        copy_number += 1
    return file_path


def is_inside(folder: Path, file_path: Path) -> bool:
    """Defense in depth: the slug already blocks traversal, this double-checks it."""
    return file_path.resolve().is_relative_to(folder.resolve())
