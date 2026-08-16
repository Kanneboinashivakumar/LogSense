"""Tests for logsense.analysis — peak hour, spike detection, severity."""

from __future__ import annotations

from logsense.analysis import (
    SpikeResult,
    classify_severity,
    detect_spikes,
    find_peak_hour,
)
from logsense.bucketing import HourBucket, bucket_by_hour
from logsense.parser import parse_logs


class TestFindPeakHour:
    """Peak hour detection picks the hour with the most errors."""

    def test_clean_spike_peak_is_hour_15(self, clean_spike_text: str) -> None:
        """sample_clean_spike.log has an obvious peak at 15:00."""
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        peak = find_peak_hour(buckets)
        assert peak == "2026-08-16 15:00"

    def test_empty_buckets_returns_none(self) -> None:
        assert find_peak_hour({}) is None

    def test_multi_spike_peak(self, multi_spike_text: str) -> None:
        """sample_multi_spike.log: one of the two spike hours should be peak."""
        result = parse_logs(multi_spike_text)
        buckets = bucket_by_hour(result.entries)
        peak = find_peak_hour(buckets)
        # Auth spike at 11:00 has 20 errors; DB spike at 14:00 has 18 errors
        assert peak == "2026-08-16 11:00"


class TestDetectSpikesHighConfidence:
    """Spike detection with ≥3 neighbors → HIGH confidence + z-score."""

    def test_clean_spike_high_confidence(self, clean_spike_text: str) -> None:
        """sample_clean_spike.log: hour 15 should be HIGH confidence spike."""
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        spike_15 = next(s for s in spikes if s.hour == "2026-08-16 15:00")
        assert spike_15.is_spike is True
        assert spike_15.confidence == "HIGH"
        assert spike_15.z_score is not None
        assert spike_15.z_score > 2.0
        assert spike_15.error_count == 35

    def test_non_spike_hours_not_flagged(self, clean_spike_text: str) -> None:
        """Normal hours in sample_clean_spike.log should not be spikes."""
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        for spike in spikes:
            if spike.hour != "2026-08-16 15:00":
                assert spike.is_spike is False, (
                    f"Hour {spike.hour} should not be a spike"
                )


class TestDetectSpikesMediumConfidence:
    """Spike detection with 1-2 neighbors → MEDIUM confidence, no z-score."""

    def test_tiny_dataset_medium_confidence(self, tiny_text: str) -> None:
        """sample_tiny.log has only 2 hours → MEDIUM or LOW confidence, no crash."""
        result = parse_logs(tiny_text)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        # There are only 2 hours (15 and 16), so each has 1 neighbor
        spike_15 = next(s for s in spikes if s.hour == "2026-08-16 15:00")
        assert spike_15.is_spike is True
        assert spike_15.confidence in ("MEDIUM", "LOW")
        # No z-score with insufficient neighbors
        assert spike_15.z_score is None
        assert spike_15.error_count == 3

    def test_zero_baseline_flags_nonzero_errors(self) -> None:
        """When all neighbors have 0 errors, any nonzero hour is a spike."""
        raw = (
            "2026-08-16 10:00:00 INFO ok\n"
            "2026-08-16 11:00:00 INFO ok\n"
            "2026-08-16 12:00:00 ERROR fail\n"
            "2026-08-16 12:30:00 ERROR fail\n"
            "2026-08-16 13:00:00 INFO ok\n"
            "2026-08-16 14:00:00 INFO ok\n"
        )
        result = parse_logs(raw)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        spike_12 = next(s for s in spikes if s.hour == "2026-08-16 12:00")
        assert spike_12.is_spike is True
        assert spike_12.confidence == "MEDIUM"
        assert spike_12.baseline == 0.0


class TestDetectSpikesLowConfidence:
    """Edge-of-dataset hour with no usable neighbors → LOW confidence."""

    def test_single_hour_dataset(self) -> None:
        """A dataset with only one hour should get LOW confidence."""
        raw = "2026-08-16 10:00:00 ERROR Database fail\n"
        result = parse_logs(raw)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        assert len(spikes) == 1
        assert spikes[0].confidence == "LOW"
        assert spikes[0].is_spike is True
        assert spikes[0].baseline is None
        assert spikes[0].z_score is None


class TestDetectSpikesNoSpike:
    """Stable dataset → no spikes flagged."""

    def test_no_spike_file(self, no_spike_text: str) -> None:
        """sample_no_spike.log has stable ~1 error/hour — no spikes expected."""
        result = parse_logs(no_spike_text)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        flagged = [s for s in spikes if s.is_spike]
        assert len(flagged) == 0, (
            f"Expected no spikes but got: "
            f"{[(s.hour, s.error_count, s.confidence) for s in flagged]}"
        )


class TestClassifySeverity:
    """Severity thresholds: <50% Normal, 50-150% Warning, >150% Critical."""

    def test_normal(self) -> None:
        assert classify_severity(30.0) == "Normal"
        assert classify_severity(0.0) == "Normal"
        assert classify_severity(-10.0) == "Normal"

    def test_warning(self) -> None:
        assert classify_severity(50.0) == "Warning"
        assert classify_severity(100.0) == "Warning"
        assert classify_severity(150.0) == "Warning"

    def test_critical(self) -> None:
        assert classify_severity(151.0) == "Critical"
        assert classify_severity(500.0) == "Critical"
        assert classify_severity(float("inf")) == "Critical"

    def test_none_defaults_to_normal(self) -> None:
        assert classify_severity(None) == "Normal"
