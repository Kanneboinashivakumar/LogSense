"""LogSense error pattern classification.

Classifies error messages into operational categories (Database, Auth,
API, Network, Other) using keyword matching.  The ``classify_pattern``
function returns the *majority* category for a set of messages.
"""

from __future__ import annotations

from collections import Counter

# ── Category keywords (all lowercase for case-insensitive matching) ───
# Order matters: we iterate these in definition order and the first
# category whose keyword appears wins for a given message.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Database": ["db", "database", "connection timeout", "sql", "postgres", "mysql", "query"],
    "Auth": ["auth", "token", "login", "unauthorized", "jwt"],
    "API": ["api", "request", "endpoint", "4xx", "5xx", "500", "503", "404"],
    "Network": ["network", "dns", "socket", "connection refused"],
}

# Fallback when no keyword matches
DEFAULT_CATEGORY: str = "Other"


def _classify_single_message(message: str) -> str:
    """Classify a single message into a category.

    Checks each category's keyword list in order.  The first match
    wins, which means the category ordering in ``CATEGORY_KEYWORDS``
    acts as a priority list (Database before Auth before API, etc.).

    Args:
        message: A single log message string.

    Returns:
        The matched category name, or ``"Other"``.
    """
    lower = message.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lower:
                return category

    return DEFAULT_CATEGORY


def classify_pattern(messages: list[str]) -> str:
    """Return the majority error category for a set of messages.

    Each message is individually classified, then the category with the
    most votes wins.  Ties are broken by whichever category appears
    first in ``Counter.most_common``.

    Args:
        messages: A list of error message strings (typically from a
            single hourly bucket).

    Returns:
        The dominant category string, or ``"Other"`` for empty input.
    """
    if not messages:
        return DEFAULT_CATEGORY

    categories = [_classify_single_message(msg) for msg in messages]
    counter = Counter(categories)
    return counter.most_common(1)[0][0]
