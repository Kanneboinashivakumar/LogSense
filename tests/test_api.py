"""Tests for the FastAPI /analyze endpoint — end-to-end API integration."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server import app

_TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


class TestAnalyzeEndpoint:
    """End-to-end API tests hitting /analyze with real test data."""

    def test_clean_spike_analysis(self, client: TestClient) -> None:
        """POST sample_clean_spike.log content and verify HIGH confidence spike."""
        raw_text = (_TEST_DATA_DIR / "sample_clean_spike.log").read_text(encoding="utf-8")
        response = client.post("/analyze", json={"raw_text": raw_text})

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "buckets" in data
        assert "peak_hour" in data
        assert "spikes" in data
        assert "incidents" in data
        assert "report" in data
        assert "warnings" in data
        assert "entry_count" in data

        # Verify peak hour
        assert data["peak_hour"] == "2026-08-16 15:00"

        # Verify incident — find the 15:00 spike (may not be first if
        # iterative refinement detected other borderline spikes)
        assert len(data["incidents"]) >= 1
        incident_15 = next(
            inc for inc in data["incidents"]
            if inc["card"]["window"] == "2026-08-16 15:00"
        )
        assert incident_15["card"]["confidence"] == "HIGH"
        assert incident_15["card"]["severity"] == "Critical"
        assert incident_15["card"]["category"] == "Database"
        assert incident_15["evidence"]["confidence"] == "HIGH"
        assert incident_15["evidence"]["z_score"] is not None

    def test_no_spike_returns_no_incidents(self, client: TestClient) -> None:
        """POST sample_no_spike.log content — no incidents expected."""
        raw_text = (_TEST_DATA_DIR / "sample_no_spike.log").read_text(encoding="utf-8")
        response = client.post("/analyze", json={"raw_text": raw_text})

        assert response.status_code == 200
        data = response.json()
        assert data["incidents"] == []

    def test_tiny_dataset_medium_confidence(self, client: TestClient) -> None:
        """POST sample_tiny.log — MEDIUM confidence, no crash."""
        raw_text = (_TEST_DATA_DIR / "sample_tiny.log").read_text(encoding="utf-8")
        response = client.post("/analyze", json={"raw_text": raw_text})

        assert response.status_code == 200
        data = response.json()
        assert len(data["incidents"]) >= 1
        incident = data["incidents"][0]
        assert incident["card"]["confidence"] in ("MEDIUM", "LOW")

    def test_multi_spike_returns_multiple_incidents(self, client: TestClient) -> None:
        """POST sample_multi_spike.log — two incidents expected."""
        raw_text = (_TEST_DATA_DIR / "sample_multi_spike.log").read_text(encoding="utf-8")
        response = client.post("/analyze", json={"raw_text": raw_text})

        assert response.status_code == 200
        data = response.json()
        assert len(data["incidents"]) >= 2

    def test_malformed_input_returns_warnings(self, client: TestClient) -> None:
        """POST sample_malformed.log — warnings present, 0 incidents (Normal severity), but buckets populated."""
        raw_text = (_TEST_DATA_DIR / "sample_malformed.log").read_text(encoding="utf-8")
        response = client.post("/analyze", json={"raw_text": raw_text})

        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) == 3
        assert data["entry_count"] == 5
        assert len(data["incidents"]) == 0
        assert "2026-08-16 15:00" in data["buckets"]
        assert data["buckets"]["2026-08-16 15:00"]["error_count"] == 4


class TestInputValidation:
    """Input validation edge cases."""

    def test_empty_input_returns_400(self, client: TestClient) -> None:
        """Empty input should return 400 with a clear message."""
        response = client.post("/analyze", json={"raw_text": ""})
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_whitespace_only_returns_400(self, client: TestClient) -> None:
        """Whitespace-only input should return 400."""
        response = client.post("/analyze", json={"raw_text": "   \n  \n  "})
        assert response.status_code == 400


class TestFileUploadEndpoint:
    """File upload via /analyze/upload."""

    def test_upload_clean_spike(self, client: TestClient) -> None:
        """Upload sample_clean_spike.log as a file."""
        filepath = _TEST_DATA_DIR / "sample_clean_spike.log"
        with open(filepath, "rb") as f:
            response = client.post(
                "/analyze/upload",
                files={"file": ("sample_clean_spike.log", f, "text/plain")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["peak_hour"] == "2026-08-16 15:00"
        assert len(data["incidents"]) >= 1
