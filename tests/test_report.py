"""Tests for logsense.report — plain-text report generation."""

from __future__ import annotations

from logsense.analysis import detect_spikes, find_peak_hour
from logsense.bucketing import bucket_by_hour
from logsense.parser import parse_logs
from logsense.report import generate_report


class TestGenerateReport:
    """The report must contain all three required sections."""

    def test_report_contains_hourly_breakdown(self, clean_spike_text: str) -> None:
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        peak = find_peak_hour(buckets)
        spikes = detect_spikes(buckets)
        report = generate_report(buckets, peak, spikes)

        assert "HOUR-WISE ERROR BREAKDOWN" in report
        # Verify at least one hour row appears
        assert "2026-08-16 15:00" in report

    def test_report_contains_peak_hour(self, clean_spike_text: str) -> None:
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        peak = find_peak_hour(buckets)
        spikes = detect_spikes(buckets)
        report = generate_report(buckets, peak, spikes)

        assert "PEAK ERROR HOUR" in report
        assert "2026-08-16 15:00" in report
        assert "35 errors" in report

    def test_report_contains_spike_alert(self, clean_spike_text: str) -> None:
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        peak = find_peak_hour(buckets)
        spikes = detect_spikes(buckets)
        report = generate_report(buckets, peak, spikes)

        assert "SPIKE ALERTS" in report
        assert "SPIKE: 2026-08-16 15:00" in report
        assert "Critical" in report

    def test_no_spike_report_says_normal(self, no_spike_text: str) -> None:
        result = parse_logs(no_spike_text)
        buckets = bucket_by_hour(result.entries)
        peak = find_peak_hour(buckets)
        spikes = detect_spikes(buckets)
        report = generate_report(buckets, peak, spikes)

        assert "No spikes detected" in report

    def test_report_on_empty_data(self) -> None:
        report = generate_report({}, None, [])
        assert "HOUR-WISE ERROR BREAKDOWN" in report
        assert "No data available" in report

    def test_tiny_dataset_report(self, tiny_text: str) -> None:
        """sample_tiny.log should produce a valid report without crashing."""
        result = parse_logs(tiny_text)
        buckets = bucket_by_hour(result.entries)
        peak = find_peak_hour(buckets)
        spikes = detect_spikes(buckets)
        report = generate_report(buckets, peak, spikes)

        assert "HOUR-WISE ERROR BREAKDOWN" in report
        assert "PEAK ERROR HOUR" in report
        assert "SPIKE ALERTS" in report
