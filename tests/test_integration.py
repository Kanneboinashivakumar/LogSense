"""Full End-to-End Pipeline Integration Tests.

Validates the full lifecycle for all 5 sample datasets:
raw file -> parse_logs -> bucket_by_hour -> find_peak_hour -> detect_spikes
-> classify_pattern -> build_incident_card -> build_evidence_panel
-> generate_report -> FastAPI POST /analyze & POST /analyze/upload.
"""
from __future__ import annotations

import io
from pathlib import Path
from fastapi.testclient import TestClient

from logsense.parser import parse_logs
from logsense.bucketing import bucket_by_hour
from logsense.analysis import find_peak_hour, detect_spikes, classify_severity
from logsense.patterns import classify_pattern
from logsense.incident import build_incident_card, build_evidence_panel
from logsense.report import generate_report
from server import app

_TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


class TestFullPipelineIntegration:
    """Complete engine-to-API integration tests across all fixtures."""

    def test_full_pipeline_clean_spike(self) -> None:
        """sample_clean_spike.log: end-to-end verification."""
        path = _TEST_DATA_DIR / "sample_clean_spike.log"
        text = path.read_text(encoding="utf-8")

        # 1. Engine parsing & bucketing
        parse_res = parse_logs(text)
        assert len(parse_res.entries) == 63
        assert len(parse_res.warnings) == 0

        buckets = bucket_by_hour(parse_res.entries)
        assert len(buckets) == 8
        assert buckets["2026-08-16 15:00"]["error_count"] == 35

        # 2. Statistical Analysis
        peak = find_peak_hour(buckets)
        assert peak == "2026-08-16 15:00"

        spikes = detect_spikes(buckets)
        spike_15 = next(s for s in spikes if s.hour == "2026-08-16 15:00")
        assert spike_15.is_spike is True
        assert spike_15.confidence == "HIGH"
        assert spike_15.z_score is not None and spike_15.z_score > 20.0

        # 3. Pattern Classification
        category = classify_pattern(buckets["2026-08-16 15:00"]["messages"])
        assert category == "Database"

        # 4. Incident Card & Evidence Panel
        card = build_incident_card(spike_15.hour, buckets, spike_15)
        panel = build_evidence_panel(card, spike_15.z_score)
        assert card["category"] == "Database"
        assert card["severity"] == "Critical"
        assert "statistically significant spike" in panel["reason"]

        # 5. Plain-Text Report
        report = generate_report(buckets, peak, spikes)
        assert "[!] SPIKE: 2026-08-16 15:00" in report
        assert "Database" not in report or "Severity" in report

        # 6. Web API (JSON payload)
        client = TestClient(app)
        api_res = client.post("/analyze", json={"raw_text": text})
        assert api_res.status_code == 200
        data = api_res.json()
        assert data["entry_count"] == 63
        assert data["peak_hour"] == "2026-08-16 15:00"
        assert len(data["incidents"]) == 1
        assert data["incidents"][0]["card"]["category"] == "Database"

        # 7. Web API (Multipart file upload)
        upload_res = client.post(
            "/analyze/upload",
            files={"file": ("sample_clean_spike.log", io.BytesIO(text.encode("utf-8")), "text/plain")},
        )
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        assert upload_data["entry_count"] == 63
        assert len(upload_data["incidents"]) == 1

    def test_full_pipeline_multi_spike(self) -> None:
        """sample_multi_spike.log: multi-spike detection and pattern differentiation."""
        text = (_TEST_DATA_DIR / "sample_multi_spike.log").read_text(encoding="utf-8")
        client = TestClient(app)
        resp = client.post("/analyze", json={"raw_text": text})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["incidents"]) >= 2

        # Verify Auth incident at 11:00
        auth_inc = next(i for i in data["incidents"] if i["card"]["window"] == "2026-08-16 11:00")
        assert auth_inc["card"]["category"] == "Auth"
        assert auth_inc["card"]["severity"] == "Critical"

        # Verify Database incident at 14:00
        db_inc = next(i for i in data["incidents"] if i["card"]["window"] == "2026-08-16 14:00")
        assert db_inc["card"]["category"] == "Database"
        assert db_inc["card"]["severity"] == "Critical"

    def test_full_pipeline_no_spike(self) -> None:
        """sample_no_spike.log: zero incidents reported."""
        text = (_TEST_DATA_DIR / "sample_no_spike.log").read_text(encoding="utf-8")
        client = TestClient(app)
        resp = client.post("/analyze", json={"raw_text": text})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["incidents"]) == 0
        assert data["entry_count"] == 20
        assert "No spikes detected" in data["report"]

    def test_full_pipeline_tiny_dataset(self) -> None:
        """sample_tiny.log: sparse data medium confidence incident."""
        text = (_TEST_DATA_DIR / "sample_tiny.log").read_text(encoding="utf-8")
        client = TestClient(app)
        resp = client.post("/analyze", json={"raw_text": text})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["incidents"]) == 1
        assert data["incidents"][0]["card"]["confidence"] in ("MEDIUM", "LOW")

    def test_full_pipeline_malformed(self) -> None:
        """sample_malformed.log: surfaces warnings, 0 false incident cards."""
        text = (_TEST_DATA_DIR / "sample_malformed.log").read_text(encoding="utf-8")
        client = TestClient(app)
        resp = client.post("/analyze", json={"raw_text": text})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["warnings"]) == 3
        assert len(data["incidents"]) == 0
        assert "2026-08-16 15:00" in data["buckets"]
