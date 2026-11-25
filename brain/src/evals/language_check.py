"""A deterministic language check: cheaper and steadier than asking the judge.

The first baseline asked the LLM judge whether each summary was in Portuguese, and it said
"no" for 10 of 12 summaries that were. A check that code can do should be done by code.
"""

import re

WORD = re.compile(r"[a-zà-ú]+")
# Common short words that exist in only one of the two languages.
PORTUGUESE_WORDS = frozenset(
    {"de", "que", "não", "uma", "um", "para", "com", "são", "é", "do", "da", "dos", "das",
     "no", "na", "em", "os", "pelo", "pela", "mais", "elas", "eles", "ela", "ele"}
)  # fmt: skip
ENGLISH_WORDS = frozenset(
    {"the", "and", "of", "to", "is", "that", "it", "with", "are", "this", "by", "from",
     "which", "they", "their", "its", "was", "were"}
)  # fmt: skip


def looks_portuguese(text: str) -> bool:
    """True when the text uses more Portuguese-only words than English-only ones."""
    words = WORD.findall(text.lower())
    portuguese = sum(1 for word in words if word in PORTUGUESE_WORDS)
    english = sum(1 for word in words if word in ENGLISH_WORDS)
    return portuguese > english
