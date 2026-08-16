"""LogSense hourly bucketing.

Groups parsed log entries into hour-sized buckets keyed by
``YYYY-MM-DD HH:00``, counting totals, errors, and warnings per bucket.
"""

from __future__ import annotations

from typing import TypedDict

from logsense.parser import LogEntry

# Format used for the bucket key (truncates to the hour)
_BUCKET_KEY_FORMAT: str = "%Y-%m-%d %H:00"


class HourBucket(TypedDict):
    """Counts for a single hourly bucket."""

    total_count: int
    error_count: int
    warning_count: int
    messages: list[str]


def bucket_by_hour(entries: list[LogEntry]) -> dict[str, HourBucket]:
    """Group log entries into hourly buckets.

    Each bucket is keyed by a string of the form ``YYYY-MM-DD HH:00``
    and contains aggregate counts plus the raw message texts (needed
    later for pattern classification).

    Args:
        entries: Parsed log entries from ``parse_logs``.

    Returns:
        An ordered dict (insertion order = chronological order) mapping
        hour keys to ``HourBucket`` dicts.
    """
    buckets: dict[str, HourBucket] = {}

    for entry in entries:
        key = entry["timestamp"].strftime(_BUCKET_KEY_FORMAT)

        if key not in buckets:
            buckets[key] = {
                "total_count": 0,
                "error_count": 0,
                "warning_count": 0,
                "messages": [],
            }

        bucket = buckets[key]
        bucket["total_count"] += 1

        if entry["level"] == "ERROR":
            bucket["error_count"] += 1
        elif entry["level"] == "WARNING":
            bucket["warning_count"] += 1

        bucket["messages"].append(entry["message"])

    return buckets
