"""LogSense FastAPI backend.

Single-file API layer that wires the Phase 1 analysis engine to an HTTP
endpoint.  Accepts raw log text via file upload or JSON body and returns
the full analysis result.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from logsense.analysis import detect_spikes, find_peak_hour
from logsense.bucketing import bucket_by_hour
from logsense.incident import build_evidence_panel, build_incident_card
from logsense.parser import parse_logs
from logsense.report import generate_report

# ── Constants ─────────────────────────────────────────────────────────
MAX_INPUT_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB cap
EMPTY_INPUT_MESSAGE: str = "Please provide log data to analyze. The input was empty."
INPUT_TOO_LARGE_MESSAGE: str = (
    f"Input exceeds the maximum allowed size of "
    f"{MAX_INPUT_SIZE_BYTES // (1024 * 1024)} MB. "
    f"Please trim your log file and try again."
)

app = FastAPI(
    title="LogSense",
    description="Log incident detection and analysis API",
    version="1.0.0",
)

# Allow CORS for local development (frontend served separately or same-origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (frontend & test data) ──────────────────────────────
_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

_TEST_DATA_DIR_PATH = Path(__file__).resolve().parent / "test_data"
if _TEST_DATA_DIR_PATH.is_dir():
    app.mount("/test_data", StaticFiles(directory=str(_TEST_DATA_DIR_PATH)), name="test_data")


# ── Request / Response models ────────────────────────────────────────
class AnalyzeTextRequest(BaseModel):
    """Request body for the paste-text analysis endpoint."""

    raw_text: str


def _sanitize_float(value: Optional[float]) -> Optional[float]:
    """Convert inf/nan floats to JSON-safe representations.

    JSON does not support Infinity or NaN, so we convert them to None
    and let the frontend handle the display.

    Args:
        value: A float that may be inf or nan, or None.

    Returns:
        The original float if finite, otherwise None.
    """
    if value is None:
        return None
    if math.isinf(value) or math.isnan(value):
        return None
    return value


def _run_analysis(raw_text: str) -> dict[str, Any]:
    """Run the full analysis pipeline and return a JSON-serializable dict.

    This is the shared logic for both the file-upload and paste-text
    endpoints.

    Args:
        raw_text: The raw log text to analyze.

    Returns:
        A dict containing all analysis results.

    Raises:
        HTTPException: If the input is empty or too large.
    """
    # ── Input validation ──────────────────────────────────────────────
    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=400, detail=EMPTY_INPUT_MESSAGE)

    if len(raw_text.encode("utf-8", errors="replace")) > MAX_INPUT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=INPUT_TOO_LARGE_MESSAGE)

    # ── Parse ─────────────────────────────────────────────────────────
    parse_result = parse_logs(raw_text)

    if not parse_result.entries:
        return {
            "buckets": {},
            "peak_hour": None,
            "spikes": [],
            "incidents": [],
            "report": "No valid log entries found to analyze.",
            "warnings": parse_result.warnings,
            "entry_count": 0,
        }

    # ── Analyze ───────────────────────────────────────────────────────
    buckets = bucket_by_hour(parse_result.entries)
    peak_hour = find_peak_hour(buckets)
    spikes = detect_spikes(buckets)

    # Build incident cards + evidence panels for flagged spikes with Warning or Critical severity
    incidents: list[dict[str, Any]] = []
    for spike in spikes:
        if spike.is_spike:
            card = build_incident_card(spike.hour, buckets, spike)
            if card["severity"] in ("Warning", "Critical"):
                panel = build_evidence_panel(card, spike.z_score)
                incidents.append({
                    "card": card,
                    "evidence": panel,
                })

    # Generate the plain-text report
    report = generate_report(buckets, peak_hour, spikes)

    # ── Serialize buckets (strip non-serializable message lists) ──────
    serialized_buckets: dict[str, dict[str, Any]] = {}
    for hour, bucket in sorted(buckets.items()):
        serialized_buckets[hour] = {
            "total_count": bucket["total_count"],
            "error_count": bucket["error_count"],
            "warning_count": bucket["warning_count"],
        }

    # ── Serialize spikes ──────────────────────────────────────────────
    serialized_spikes: list[dict[str, Any]] = []
    for spike in spikes:
        serialized_spikes.append({
            "hour": spike.hour,
            "is_spike": spike.is_spike,
            "error_count": spike.error_count,
            "baseline": _sanitize_float(spike.baseline),
            "deviation_pct": _sanitize_float(spike.deviation_pct),
            "z_score": _sanitize_float(spike.z_score),
            "confidence": spike.confidence,
        })

    # ── Sanitize incident floats ──────────────────────────────────────
    for inc in incidents:
        for key in ("deviation_pct", "z_score"):
            if key in inc["card"]:
                inc["card"][key] = _sanitize_float(inc["card"].get(key))
            if key in inc["evidence"]:
                inc["evidence"][key] = _sanitize_float(inc["evidence"].get(key))
        if "local_baseline" in inc["evidence"]:
            inc["evidence"]["local_baseline"] = _sanitize_float(
                inc["evidence"].get("local_baseline")
            )

    return {
        "buckets": serialized_buckets,
        "peak_hour": peak_hour,
        "spikes": serialized_spikes,
        "incidents": incidents,
        "report": report,
        "warnings": parse_result.warnings,
        "entry_count": len(parse_result.entries),
    }


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend() -> FileResponse:
    """Serve the main frontend HTML file."""
    index_path = _STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(str(index_path))


@app.get("/favicon.ico")
async def serve_favicon() -> FileResponse:
    """Serve the application favicon."""
    fav_path = _STATIC_DIR / "favicon.ico"
    if not fav_path.exists():
        fav_path = _STATIC_DIR / "assets" / "logo.png"
    return FileResponse(str(fav_path))


@app.post("/analyze")
async def analyze_text(request: AnalyzeTextRequest) -> JSONResponse:
    """Analyze raw log text submitted as a JSON body.

    Args:
        request: JSON body with ``raw_text`` field.

    Returns:
        JSON response with full analysis results.
    """
    result = _run_analysis(request.raw_text)
    return JSONResponse(content=result)


@app.post("/analyze/upload")
async def analyze_upload(file: UploadFile = File(...)) -> JSONResponse:
    """Analyze a log file uploaded via multipart form data.

    Args:
        file: The uploaded log file.

    Returns:
        JSON response with full analysis results.
    """
    try:
        contents = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read uploaded file: {exc}",
        )

    if len(contents) > MAX_INPUT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=INPUT_TOO_LARGE_MESSAGE)

    raw_text = contents.decode("utf-8", errors="replace")
    result = _run_analysis(raw_text)
    return JSONResponse(content=result)
