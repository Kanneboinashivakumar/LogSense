"""Tests for logsense.bucketing — hourly bucket aggregation."""

from __future__ import annotations

from datetime import datetime

from logsense.bucketing import bucket_by_hour
from logsense.parser import LogEntry, parse_logs


class TestBucketByHour:
    """Bucketing groups entries by hour and counts correctly."""

    def test_hand_verifiable_small_dataset(self) -> None:
        """Five entries across two hours — verify exact counts."""
        entries: list[LogEntry] = [
            {"timestamp": datetime(2026, 8, 16, 10, 0, 0), "level": "INFO", "message": "ok"},
            {"timestamp": datetime(2026, 8, 16, 10, 15, 0), "level": "ERROR", "message": "fail"},
            {"timestamp": datetime(2026, 8, 16, 10, 30, 0), "level": "WARNING", "message": "slow"},
            {"timestamp": datetime(2026, 8, 16, 11, 0, 0), "level": "ERROR", "message": "fail"},
            {"timestamp": datetime(2026, 8, 16, 11, 30, 0), "level": "ERROR", "message": "fail"},
        ]

        buckets = bucket_by_hour(entries)

        assert "2026-08-16 10:00" in buckets
        assert "2026-08-16 11:00" in buckets

        h10 = buckets["2026-08-16 10:00"]
        assert h10["total_count"] == 3
        assert h10["error_count"] == 1
        assert h10["warning_count"] == 1

        h11 = buckets["2026-08-16 11:00"]
        assert h11["total_count"] == 2
        assert h11["error_count"] == 2
        assert h11["warning_count"] == 0

    def test_clean_spike_bucket_counts(self, clean_spike_text: str) -> None:
        """Verify sample_clean_spike.log bucket counts against hand-analysis."""
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)

        # Hour 15 should have 35 entries, all ERROR
        h15 = buckets["2026-08-16 15:00"]
        assert h15["total_count"] == 35
        assert h15["error_count"] == 35
        assert h15["warning_count"] == 0

        # Hour 11 should have 4 entries: 1 ERROR, 1 WARNING, 2 INFO
        h11 = buckets["2026-08-16 11:00"]
        assert h11["total_count"] == 4
        assert h11["error_count"] == 1
        assert h11["warning_count"] == 1

    def test_empty_entries_gives_empty_buckets(self) -> None:
        """Empty input produces empty buckets dict."""
        buckets = bucket_by_hour([])
        assert buckets == {}

    def test_messages_are_collected(self) -> None:
        """Bucket stores all message strings for pattern classification."""
        entries: list[LogEntry] = [
            {"timestamp": datetime(2026, 8, 16, 10, 0, 0), "level": "ERROR", "message": "db timeout"},
            {"timestamp": datetime(2026, 8, 16, 10, 30, 0), "level": "ERROR", "message": "auth failed"},
        ]
        buckets = bucket_by_hour(entries)
        assert buckets["2026-08-16 10:00"]["messages"] == ["db timeout", "auth failed"]
