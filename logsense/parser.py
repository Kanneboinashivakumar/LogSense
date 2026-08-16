"""LogSense log parser.

Parses raw log text into structured entries, skipping malformed lines
and collecting warnings for the caller to surface to users.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict


# Regex for the canonical log format: "YYYY-MM-DD HH:MM:SS LEVEL MESSAGE"
_LOG_LINE_PATTERN: re.Pattern[str] = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(INFO|WARNING|ERROR)\s+(.+)$"
)

# The datetime format produced by the regex capture group
_TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"

VALID_LEVELS: frozenset[str] = frozenset({"INFO", "WARNING", "ERROR"})


class LogEntry(TypedDict):
    """A single parsed log entry."""

    timestamp: datetime
    level: str
    message: str


@dataclass
class ParseResult:
    """Result of parsing raw log text.

    Attributes:
        entries: Successfully parsed log entries.
        warnings: Human-readable warnings about lines that were skipped.
    """

    entries: list[LogEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_logs(raw_text: str) -> ParseResult:
    """Parse raw log text into structured entries.

    Each non-empty line is matched against the canonical format
    ``YYYY-MM-DD HH:MM:SS LEVEL MESSAGE``. Lines that don't match
    are collected as warnings rather than raising exceptions so that
    partially-valid log files still yield useful analysis.

    Args:
        raw_text: The full log text, one entry per line.

    Returns:
        A ``ParseResult`` with the valid entries and any warnings.
    """
    result = ParseResult()

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            # Blank lines are silently skipped — not worth warning about.
            continue

        match = _LOG_LINE_PATTERN.match(line)
        if match is None:
            result.warnings.append(
                f"Line {line_number}: skipped malformed entry: {line!r}"
            )
            continue

        timestamp_str, level, message = match.groups()

        try:
            timestamp = datetime.strptime(timestamp_str, _TIMESTAMP_FORMAT)
        except ValueError:
            result.warnings.append(
                f"Line {line_number}: skipped entry with unparseable "
                f"timestamp: {timestamp_str!r}"
            )
            continue

        entry: LogEntry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
        }
        result.entries.append(entry)

    return result
