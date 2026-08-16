"""Tests for logsense.parser — log line parsing and malformed-line handling."""

from __future__ import annotations

from datetime import datetime

from logsense.parser import ParseResult, parse_logs


class TestParseValidLines:
    """Parsing well-formed log lines."""

    def test_single_valid_line(self) -> None:
        raw = "2026-08-16 15:02:11 ERROR Database connection timeout"
        result = parse_logs(raw)

        assert len(result.entries) == 1
        assert result.entries[0]["timestamp"] == datetime(2026, 8, 16, 15, 2, 11)
        assert result.entries[0]["level"] == "ERROR"
        assert result.entries[0]["message"] == "Database connection timeout"
        assert result.warnings == []

    def test_all_three_levels(self) -> None:
        raw = (
            "2026-08-16 10:00:00 INFO Health check passed\n"
            "2026-08-16 10:01:00 WARNING Slow query detected\n"
            "2026-08-16 10:02:00 ERROR API request failed: 500\n"
        )
        result = parse_logs(raw)
        levels = [e["level"] for e in result.entries]
        assert levels == ["INFO", "WARNING", "ERROR"]
        assert result.warnings == []

    def test_clean_spike_file_parses_fully(self, clean_spike_text: str) -> None:
        """All 63 data lines of sample_clean_spike.log should parse without warnings."""
        result = parse_logs(clean_spike_text)
        # The file has 63 non-empty data lines (trailing newline is blank)
        assert len(result.entries) == 63
        assert result.warnings == []

    def test_no_spike_file_parses_fully(self, no_spike_text: str) -> None:
        """All 20 lines of sample_no_spike.log should parse without warnings."""
        result = parse_logs(no_spike_text)
        assert len(result.entries) == 20
        assert result.warnings == []


class TestParseMalformedLines:
    """Malformed and garbage lines are skipped with warnings."""

    def test_malformed_file_skips_bad_lines(self, malformed_text: str) -> None:
        """sample_malformed.log has 5 valid lines and 3 garbage lines."""
        result = parse_logs(malformed_text)
        assert len(result.entries) == 5
        assert len(result.warnings) == 3

    def test_garbage_line_produces_warning(self) -> None:
        raw = "this is complete garbage"
        result = parse_logs(raw)
        assert len(result.entries) == 0
        assert len(result.warnings) == 1
        assert "skipped malformed entry" in result.warnings[0]

    def test_bad_level_is_rejected(self) -> None:
        raw = "2026-08-16 10:00:00 BADLEVEL something happened"
        result = parse_logs(raw)
        assert len(result.entries) == 0
        assert len(result.warnings) == 1

    def test_mixed_valid_and_invalid(self) -> None:
        raw = (
            "2026-08-16 10:00:00 INFO Good line\n"
            "not a log line\n"
            "2026-08-16 10:01:00 ERROR Another good line\n"
        )
        result = parse_logs(raw)
        assert len(result.entries) == 2
        assert len(result.warnings) == 1


class TestParseEmptyInput:
    """Empty and whitespace-only inputs."""

    def test_empty_string(self) -> None:
        result = parse_logs("")
        assert result.entries == []
        assert result.warnings == []

    def test_whitespace_only(self) -> None:
        result = parse_logs("   \n  \n\n  ")
        assert result.entries == []
        assert result.warnings == []

    def test_empty_file(self, empty_text: str) -> None:
        result = parse_logs(empty_text)
        assert result.entries == []
        assert result.warnings == []
