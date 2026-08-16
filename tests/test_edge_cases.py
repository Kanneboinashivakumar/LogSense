"""Edge-case and boundary hardening tests for LogSense.

Covers all 9 mandated edge cases:
1. Empty input / whitespace-only (CLI & API return clean error, no crash).
2. Single-line log file (LOW confidence, no division-by-zero).
3. All-error log file (100% error rate, no overflow or math errors).
4. All-INFO log file (0 errors, peak hour handling, normal traffic report).
5. Timestamps out of order (non-chronological log stream bucketed and sorted).
6. Multi-day logs spanning midnight (YYYY-MM-DD HH:00 bucket keys, no collision).
7. Massive single-line message (10KB+ string without choking).
8. Unknown log levels ("TRACE", "FATAL", "CRITICAL", "DEBUG") skipped with warning.
9. Extremely high error counts (millions of errors, JSON serialization safe, no NaN/inf crashes).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from fastapi.testclient import TestClient

from logsense.parser import parse_logs
from logsense.bucketing import bucket_by_hour
from logsense.analysis import (
    find_peak_hour,
    detect_spikes,
    classify_severity,
    calculate_baseline_deviation,
)
from logsense.patterns import classify_pattern
from logsense.incident import build_incident_card, build_evidence_panel
from logsense.report import generate_report
from server import app


class TestEdgeCase1EmptyInput:
    """1. Empty input / whitespace-only handling."""

    def test_empty_string_parser(self) -> None:
        res = parse_logs("")
        assert res.entries == []
        assert res.warnings == []

    def test_whitespace_only_parser(self) -> None:
        res = parse_logs("   \n\t  \n  \n")
        assert res.entries == []
        assert res.warnings == []

    def test_empty_input_api_returns_400(self) -> None:
        client = TestClient(app)
        resp = client.post("/analyze", json={"raw_text": ""})
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_whitespace_input_api_returns_400(self) -> None:
        client = TestClient(app)
        resp = client.post("/analyze", json={"raw_text": "   \n\n\t  "})
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()


class TestEdgeCase2SingleLineLogFile:
    """2. Single-line log file (confidence LOW, no div-by-zero)."""

    def test_single_error_entry(self) -> None:
        raw = "2026-08-16 10:15:00 ERROR Database connection timeout"
        res = parse_logs(raw)
        assert len(res.entries) == 1

        buckets = bucket_by_hour(res.entries)
        assert len(buckets) == 1
        assert "2026-08-16 10:00" in buckets

        spikes = detect_spikes(buckets)
        assert len(spikes) == 1
        spike = spikes[0]
        assert spike.confidence == "LOW"
        assert spike.baseline is None
        assert spike.z_score is None

        # Should not flag as incident because Normal severity (no baseline)
        card = build_incident_card(spike.hour, buckets, spike)
        assert card["severity"] == "Normal"
        assert card["confidence"] == "LOW"

    def test_single_info_entry(self) -> None:
        raw = "2026-08-16 10:15:00 INFO System started"
        res = parse_logs(raw)
        buckets = bucket_by_hour(res.entries)
        spikes = detect_spikes(buckets)
        assert len(spikes) == 1
        assert spikes[0].error_count == 0
        assert spikes[0].is_spike is False


class TestEdgeCase3AllErrorLogFile:
    """3. All-error log file (100% error rate)."""

    def test_all_errors_multiple_hours(self) -> None:
        lines = [
            f"2026-08-16 {h:02d}:10:00 ERROR Database timeout error"
            for h in range(10, 16)
        ]
        raw = "\n".join(lines)
        res = parse_logs(raw)
        assert len(res.entries) == 6

        buckets = bucket_by_hour(res.entries)
        assert len(buckets) == 6
        for b in buckets.values():
            assert b["error_count"] == 1
            assert b["total_count"] == 1

        # Stable flat line of 1 error per hour -> standard deviation = 0 -> no spike
        spikes = detect_spikes(buckets)
        assert all(s.is_spike is False for s in spikes)

    def test_all_errors_with_one_massive_peak(self) -> None:
        lines = [
            f"2026-08-16 {h:02d}:10:00 ERROR Auth failure"
            for h in range(10, 15)
        ]
        # Hour 15 has 50 errors
        lines.extend([
            f"2026-08-16 15:{m:02d}:00 ERROR Auth failure"
            for m in range(50)
        ])
        raw = "\n".join(lines)
        res = parse_logs(raw)
        buckets = bucket_by_hour(res.entries)
        spikes = detect_spikes(buckets)

        spike_15 = next(s for s in spikes if s.hour == "2026-08-16 15:00")
        assert spike_15.is_spike is True
        assert spike_15.confidence == "HIGH"
        assert spike_15.error_count == 50


class TestEdgeCase4AllInfoLogFile:
    """4. All-INFO log file (zero errors everywhere)."""

    def test_all_info_no_errors(self) -> None:
        lines = [
            f"2026-08-16 {h:02d}:05:00 INFO Health check status ok"
            for h in range(8, 16)
        ]
        raw = "\n".join(lines)
        res = parse_logs(raw)
        assert len(res.entries) == 8

        buckets = bucket_by_hour(res.entries)
        peak = find_peak_hour(buckets)
        assert peak is not None
        assert buckets[peak]["error_count"] == 0

        spikes = detect_spikes(buckets)
        assert all(s.is_spike is False for s in spikes)
        assert all(s.error_count == 0 for s in spikes)

        report = generate_report(buckets, peak, spikes)
        assert "No spikes detected -- traffic appears normal." in report


class TestEdgeCase5TimestampsOutOfOrder:
    """5. Timestamps out of order in log stream."""

    def test_shuffled_log_entries_bucketed_accurately(self) -> None:
        # Shuffled timestamps
        raw = (
            "2026-08-16 14:00:00 ERROR DB error in hour 14\n"
            "2026-08-16 10:00:00 INFO OK in hour 10\n"
            "2026-08-16 12:00:00 WARNING High memory in hour 12\n"
            "2026-08-16 10:30:00 ERROR DB error in hour 10\n"
            "2026-08-16 14:45:00 ERROR DB error in hour 14\n"
        )
        res = parse_logs(raw)
        assert len(res.entries) == 5

        buckets = bucket_by_hour(res.entries)
        # Bucketing correctly aggregates regardless of input ordering
        assert buckets["2026-08-16 10:00"]["total_count"] == 2
        assert buckets["2026-08-16 10:00"]["error_count"] == 1
        assert buckets["2026-08-16 12:00"]["warning_count"] == 1
        assert buckets["2026-08-16 14:00"]["error_count"] == 2

        # Spikes analysis sorts the bucket keys internally
        spikes = detect_spikes(buckets)
        sorted_spike_hours = [s.hour for s in spikes]
        assert sorted_spike_hours == ["2026-08-16 10:00", "2026-08-16 12:00", "2026-08-16 14:00"]


class TestEdgeCase6MultiDayLogs:
    """6. Multi-day logs spanning across midnight (YYYY-MM-DD HH:00)."""

    def test_midnight_rollover_no_bucket_collision(self) -> None:
        raw = (
            "2026-08-16 23:30:00 ERROR Fail before midnight\n"
            "2026-08-16 23:45:00 ERROR Fail before midnight\n"
            "2026-08-17 00:15:00 INFO New day starts\n"
            "2026-08-17 23:30:00 ERROR Fail 24 hours later\n"
        )
        res = parse_logs(raw)
        buckets = bucket_by_hour(res.entries)

        # Confirm 2026-08-16 23:00 and 2026-08-17 23:00 are distinct buckets
        assert "2026-08-16 23:00" in buckets
        assert "2026-08-17 00:00" in buckets
        assert "2026-08-17 23:00" in buckets
        assert len(buckets) == 3

        assert buckets["2026-08-16 23:00"]["error_count"] == 2
        assert buckets["2026-08-17 23:00"]["error_count"] == 1


class TestEdgeCase7MassiveSingleLineMessage:
    """7. Massive single-line message (10KB string)."""

    def test_10kb_single_line_message(self) -> None:
        huge_payload = "A" * 10240  # 10 KB string
        raw = f"2026-08-16 10:00:00 ERROR Database query error with giant trace: {huge_payload}"
        res = parse_logs(raw)

        assert len(res.entries) == 1
        assert len(res.warnings) == 0
        assert res.entries[0]["level"] == "ERROR"
        assert len(res.entries[0]["message"]) >= 10240

        # Pattern classifier parses without choking
        cat = classify_pattern([res.entries[0]["message"]])
        assert cat == "Database"


class TestEdgeCase8UnknownLogLevels:
    """8. Unknown log levels (TRACE, FATAL, CRITICAL, DEBUG, NOTICE)."""

    def test_unknown_levels_produce_warnings_without_crashing(self) -> None:
        raw = (
            "2026-08-16 10:00:00 TRACE Entering method foo\n"
            "2026-08-16 10:01:00 FATAL Kernel panic in thread 4\n"
            "2026-08-16 10:02:00 CRITICAL Out of memory killer invoked\n"
            "2026-08-16 10:03:00 DEBUG Cache lookup miss\n"
            "2026-08-16 10:04:00 NOTICE Service reloading configuration\n"
            "2026-08-16 10:05:00 ERROR Database connection failed\n"
        )
        res = parse_logs(raw)

        # 5 unknown levels produce 5 warnings
        assert len(res.warnings) == 5
        # 1 valid ERROR entry is preserved
        assert len(res.entries) == 1
        assert res.entries[0]["level"] == "ERROR"


class TestEdgeCase9ExtremelyHighErrorCounts:
    """9. Extremely high error counts (millions of errors, JSON safe)."""

    def test_large_error_counts_math_and_json_safety(self) -> None:
        buckets = {
            "2026-08-16 10:00": {"total_count": 1000000, "error_count": 1000000, "warning_count": 0, "messages": ["Database timeout"]},
            "2026-08-16 11:00": {"total_count": 1000000, "error_count": 1000000, "warning_count": 0, "messages": ["Database timeout"]},
            "2026-08-16 12:00": {"total_count": 50000000, "error_count": 50000000, "warning_count": 0, "messages": ["Database deadlocked"]},
            "2026-08-16 13:00": {"total_count": 1000000, "error_count": 1000000, "warning_count": 0, "messages": ["Database timeout"]},
            "2026-08-16 14:00": {"total_count": 1000000, "error_count": 1000000, "warning_count": 0, "messages": ["Database timeout"]},
        }

        spikes = detect_spikes(buckets)
        spike_12 = next(s for s in spikes if s.hour == "2026-08-16 12:00")
        assert spike_12.is_spike is True
        assert spike_12.confidence == "HIGH"
        assert spike_12.z_score is not None

        # Build incident card and evidence panel
        card = build_incident_card(spike_12.hour, buckets, spike_12)
        panel = build_evidence_panel(card, spike_12.z_score)

        # Test JSON serialization
        payload = {"card": card, "evidence": panel}
        json_str = json.dumps(payload)
        assert json_str is not None
        decoded = json.loads(json_str)
        assert decoded["card"]["error_count"] == 50000000
