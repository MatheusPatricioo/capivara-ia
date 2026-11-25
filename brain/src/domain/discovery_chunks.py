"""Chunking: a discovery is searched in pieces, so one specific detail can still be found.

A single embedding for the whole text averages every subject in it: a summary about
capybaras that also mentions their friendship with birds barely matches "birds on a
capybara's back". Each piece gets a "contextual header" (title and topic), so a piece like
"Elas deixam." still knows what it is about.

The whole text is always the first piece, so chunking never loses what the single
embedding already found.
"""

import re

from src.domain.discovery import Discovery
from src.domain.discovery_memory import memory_text

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
SENTENCES_PER_CHUNK = 2


def discovery_chunks(discovery: Discovery) -> list[str]:
    """The whole text first, then overlapping windows of two sentences, each with a header.

    The first piece is exactly memory_text(discovery), the text the whole-discovery
    embedding uses. A summary with two sentences or fewer is a single piece: a window
    would only repeat it.
    """
    header = f"{discovery.title}\n{discovery.topic}"
    sentences = [sentence for sentence in SENTENCE_END.split(discovery.summary.strip()) if sentence]
    chunks = [memory_text(discovery)]
    if len(sentences) <= SENTENCES_PER_CHUNK:
        return chunks
    last_start = len(sentences) - SENTENCES_PER_CHUNK
    for start in range(last_start + 1):
        window = " ".join(sentences[start : start + SENTENCES_PER_CHUNK])
        chunks.append(f"{header}\n{window}")
    return chunks
