"""Downloads a small sample of Quick, Draw! doodles (Google, CC BY 4.0) for the chalkboard.

Run from the brain folder:  python -m src.download_quickdraw_sample
Each category file is streamed and the download stops after the first usable doodles, so
only a few MB are transferred instead of the full dataset.
"""

import logging

import httpx

from src.domain.doodle import Doodle
from src.infrastructure.quickdraw_doodles import (
    DEFAULT_SAMPLE_FILE,
    QUICKDRAW_CATEGORIES_URL,
    QUICKDRAW_SIMPLIFIED_URL,
    sample_doodles,
    save_doodle_sample,
)

DOODLES_PER_CATEGORY = 30
REQUEST_TIMEOUT_SECONDS = 60.0

logger = logging.getLogger(__name__)


def download_category(client: httpx.Client, category: str) -> list[Doodle]:
    url = QUICKDRAW_SIMPLIFIED_URL.format(category=category.replace(" ", "%20"))
    with client.stream("GET", url) as response:
        response.raise_for_status()
        return sample_doodles(category, response.iter_lines(), DOODLES_PER_CATEGORY)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    doodles_by_category: dict[str, list[Doodle]] = {}
    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        categories = client.get(QUICKDRAW_CATEGORIES_URL).raise_for_status().text.split("\n")
        categories = [category.strip() for category in categories if category.strip()]
        for position, category in enumerate(categories, start=1):
            try:
                doodles_by_category[category] = download_category(client, category)
            except httpx.HTTPError as error:
                logger.warning("Skipped '%s': %s", category, error)
                continue
            logger.info(
                "%d/%d %s: %d doodles",
                position,
                len(categories),
                category,
                len(doodles_by_category[category]),
            )
    save_doodle_sample(doodles_by_category)
    logger.info("Saved %d categories to %s", len(doodles_by_category), DEFAULT_SAMPLE_FILE)


if __name__ == "__main__":
    main()
