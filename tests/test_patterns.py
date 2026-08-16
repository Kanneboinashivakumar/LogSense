"""Tests for logsense.patterns — error message classification."""

from __future__ import annotations

from logsense.patterns import classify_pattern, _classify_single_message


class TestClassifySingleMessage:
    """Individual message classification by keyword matching."""

    def test_database_keywords(self) -> None:
        assert _classify_single_message("Database connection timeout") == "Database"
        assert _classify_single_message("slow SQL query detected") == "Database"
        assert _classify_single_message("postgres replication lag") == "Database"

    def test_auth_keywords(self) -> None:
        assert _classify_single_message("Auth token expired") == "Auth"
        assert _classify_single_message("unauthorized access attempt") == "Auth"
        assert _classify_single_message("JWT validation failed") == "Auth"

    def test_api_keywords(self) -> None:
        assert _classify_single_message("API request failed: 500") == "API"
        assert _classify_single_message("endpoint not found") == "API"

    def test_network_keywords(self) -> None:
        assert _classify_single_message("DNS resolution failed") == "Network"
        assert _classify_single_message("connection refused by host") == "Network"

    def test_fallback_to_other(self) -> None:
        assert _classify_single_message("something completely unknown") == "Other"

    def test_case_insensitive(self) -> None:
        assert _classify_single_message("DATABASE CONNECTION TIMEOUT") == "Database"


class TestClassifyPattern:
    """Majority-vote classification across multiple messages."""

    def test_majority_database(self) -> None:
        """Majority of messages are Database-related → Database."""
        messages = [
            "Database connection timeout",
            "Database connection timeout",
            "Database connection timeout",
            "Auth token expired",
            "API request failed: 500",
        ]
        assert classify_pattern(messages) == "Database"

    def test_majority_auth(self) -> None:
        messages = [
            "Auth token expired: invalid signature",
            "Auth token expired: invalid signature",
            "Auth token expired: invalid signature",
            "API request failed: 500",
        ]
        assert classify_pattern(messages) == "Auth"

    def test_empty_messages(self) -> None:
        assert classify_pattern([]) == "Other"

    def test_single_message(self) -> None:
        assert classify_pattern(["DNS resolution failed"]) == "Network"

    def test_clean_spike_hour15_pattern(self, clean_spike_text: str) -> None:
        """Hour 15 of sample_clean_spike.log is dominated by Database errors."""
        from logsense.parser import parse_logs
        from logsense.bucketing import bucket_by_hour

        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        messages_15 = buckets["2026-08-16 15:00"]["messages"]
        pattern = classify_pattern(messages_15)
        assert pattern == "Database"
