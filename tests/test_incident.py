"""Tests for logsense.incident — incident card and evidence panel building."""

from __future__ import annotations

from logsense.analysis import detect_spikes
from logsense.bucketing import bucket_by_hour
from logsense.incident import build_evidence_panel, build_incident_card
from logsense.parser import parse_logs


class TestBuildIncidentCard:
    """Incident card assembly from spike results."""

    def test_clean_spike_incident_card(self, clean_spike_text: str) -> None:
        """Incident card for hour 15 of sample_clean_spike.log."""
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        spike_15 = next(s for s in spikes if s.hour == "2026-08-16 15:00")
        card = build_incident_card("2026-08-16 15:00", buckets, spike_15)

        assert card["category"] == "Database"
        assert card["severity"] == "Critical"
        assert card["window"] == "2026-08-16 15:00"
        assert card["error_count"] == 35
        assert card["confidence"] == "HIGH"

    def test_tiny_dataset_incident_card(self, tiny_text: str) -> None:
        """Incident card for the sparse sample_tiny.log."""
        result = parse_logs(tiny_text)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        spike_15 = next(s for s in spikes if s.hour == "2026-08-16 15:00")
        card = build_incident_card("2026-08-16 15:00", buckets, spike_15)

        assert card["confidence"] in ("MEDIUM", "LOW")
        assert card["error_count"] == 3

    def test_incident_category_uses_only_error_messages(self) -> None:
        """Category must reflect only ERROR messages, ignoring INFO/WARNING noise."""
        raw_lines = [
            # 5 INFO messages with "auth" keywords
            "2026-08-16 15:01:00 INFO User login successful auth token validated\n",
            "2026-08-16 15:02:00 INFO User login successful auth session active\n",
            "2026-08-16 15:03:00 INFO Authentication token refreshed for user\n",
            "2026-08-16 15:04:00 INFO Auth credentials verified\n",
            "2026-08-16 15:05:00 INFO User authentication token granted\n",
            # 2 ERROR messages with "database" keywords
            "2026-08-16 15:10:00 ERROR PostgreSQL connection pool exhausted\n",
            "2026-08-16 15:11:00 ERROR DB query timeout on database cluster\n",
        ]
        result = parse_logs("".join(raw_lines))
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)
        spike = spikes[0]

        card = build_incident_card(spike.hour, buckets, spike)

        # Majority of all messages (5/7) are Auth, but all ERROR messages (2/2) are Database
        assert card["category"] == "Database"


class TestBuildEvidencePanel:
    """Evidence panel with confidence-aware reason wording."""

    def test_high_confidence_reason_mentions_zscore(self, clean_spike_text: str) -> None:
        """HIGH confidence reason should mention z-score, not 'limited data'."""
        result = parse_logs(clean_spike_text)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        spike_15 = next(s for s in spikes if s.hour == "2026-08-16 15:00")
        card = build_incident_card("2026-08-16 15:00", buckets, spike_15)
        panel = build_evidence_panel(card, spike_15.z_score)

        assert panel["confidence"] == "HIGH"
        assert "z-score" in panel["reason"]
        assert "limited" not in panel["reason"].lower()

    def test_medium_confidence_reason_mentions_limited_data(self, tiny_text: str) -> None:
        """MEDIUM confidence reason should mention 'limited surrounding data'."""
        result = parse_logs(tiny_text)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        spike_15 = next(s for s in spikes if s.hour == "2026-08-16 15:00")
        card = build_incident_card("2026-08-16 15:00", buckets, spike_15)
        panel = build_evidence_panel(card, spike_15.z_score)

        assert panel["confidence"] in ("MEDIUM", "LOW")
        reason_lower = panel["reason"].lower()
        assert "limited" in reason_lower or "no comparable" in reason_lower

    def test_low_confidence_reason(self) -> None:
        """LOW confidence reason should mention 'no comparable surrounding data'."""
        raw = "2026-08-16 10:00:00 ERROR Something broke\n"
        result = parse_logs(raw)
        buckets = bucket_by_hour(result.entries)
        spikes = detect_spikes(buckets)

        spike = spikes[0]
        card = build_incident_card(spike.hour, buckets, spike)
        panel = build_evidence_panel(card, spike.z_score)

        assert panel["confidence"] == "LOW"
        assert "no comparable" in panel["reason"].lower()
