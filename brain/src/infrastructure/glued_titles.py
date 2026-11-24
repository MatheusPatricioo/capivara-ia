"""Undoes a quirk of the ddgs DuckDuckGo parser: several titles glued into one.

ddgs joins every piece of text under the <h2> tags of a result with "" (no space), because
one title also comes in pieces (the words of the query are in bold). When DuckDuckGo puts
several titles in the same result block, they come out glued:

    "Lua: características, fases, eclipse, origem e mais - Toda ...Lua: características,
     fases, origem, formação - Brasil Escola..."

The real title is the first one. Measured on the search log: 6 glued titles in 24 searches.
"""

import re

MAX_TITLE_LENGTH = 80
"""DuckDuckGo cuts long titles with " ..." around 65 characters, so a longer one is glued."""
ELLIPSIS_GLUE = re.compile(r"\.\.\.(?=\S)")
"""A cut title ("Toda ...") followed right away by the next title, with no space."""
CASE_GLUE = re.compile(r"(?<=[a-zà-ÿ0-9?!)])(?=[A-ZÀ-Þ])")
"""A lowercase letter touching an uppercase one ("servemSatélites"). Last resort only:
real titles have them too ("YouTube", "SlideShare", "ResearchGate")."""


def first_title(title: str, other_titles: list[str]) -> str:
    """The first title of a glued title, or the title itself when it is not glued.

    The reliable signs come first: where another result's title starts, or where a cut
    title ("...") touches the next one. The case change is used only when neither shows up.
    """
    if len(title) <= MAX_TITLE_LENGTH:
        return title
    reliable_cuts = _other_title_positions(title, other_titles) + _ellipsis_glue_positions(title)
    if reliable_cuts:
        return title[: min(reliable_cuts)].strip()
    case_glue = CASE_GLUE.search(title)
    if case_glue:
        return title[: case_glue.start()].strip()
    return title


def _other_title_positions(title: str, other_titles: list[str]) -> list[int]:
    positions = (title.find(other, 1) for other in other_titles if other and other != title)
    return [position for position in positions if position > 0]


def _ellipsis_glue_positions(title: str) -> list[int]:
    first_glue = ELLIPSIS_GLUE.search(title)
    return [first_glue.end()] if first_glue else []
