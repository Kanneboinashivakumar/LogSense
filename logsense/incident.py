"""LogSense incident card and evidence panel builder.

Assembles the high-level incident summary (card) and the detailed
evidence panel (the "why was this flagged?" explanation) from the
analysis results.
"""

from __future__ import annotations

from typing import Any, Optional

from logsense.analysis import SpikeResult, classify_severity
from logsense.bucketing import HourBucket
from logsense.patterns import classify_pattern


def build_incident_card(
    hour: str,
    buckets: dict[str, HourBucket],
    spike: SpikeResult,
) -> dict[str, Any]:
    """Build a summary incident card for a spike hour.

    Args:
        hour: The bucket key of the spike hour.
        buckets: All hourly buckets.
        spike: The ``SpikeResult`` for this hour.

    Returns:
        A dict with ``category``, ``severity``, ``deviation_pct``,
        ``window``, ``error_count``, ``baseline``, and ``confidence``.
    """
    error_messages = [
        msg for msg in buckets[hour]["messages"]
        # Only classify ERROR-level messages for the pattern
    ]
    category = classify_pattern(error_messages)
    severity = classify_severity(spike.deviation_pct)

    return {
        "category": category,
        "severity": severity,
        "deviation_pct": spike.deviation_pct,
        "window": hour,
        "error_count": spike.error_count,
        "baseline": spike.baseline,
        "confidence": spike.confidence,
    }


def build_evidence_panel(
    incident_card: dict[str, Any],
    z_score: Optional[float],
) -> dict[str, Any]:
    """Build the detailed evidence panel for an incident.

    The evidence panel is the "why was this flagged?" expandable section.
    It includes all the statistical backing and a plain-English reason
    sentence whose wording intentionally varies by confidence tier:

    - **HIGH**: States the z-score and that there is sufficient data.
    - **MEDIUM / LOW**: Mentions that surrounding data is limited and
      the detection should be interpreted with caution.

    Args:
        incident_card: The card dict from ``build_incident_card``.
        z_score: The z-score value, or ``None`` when unavailable.

    Returns:
        A dict with ``error_count``, ``local_baseline``,
        ``deviation_pct``, ``z_score``, ``confidence``,
        ``dominant_pattern``, ``severity``, and ``reason``.
    """
    confidence = incident_card["confidence"]
    error_count = incident_card["error_count"]
    baseline = incident_card["baseline"]
    deviation_pct = incident_card["deviation_pct"]
    category = incident_card["category"]

    # ── Build the plain-English reason ────────────────────────────────
    if confidence == "HIGH":
        z_str = f"{z_score:.1f}" if z_score is not None else "N/A"
        reason = (
            f"{error_count} errors in this hour vs a local baseline of "
            f"{baseline:.1f} (z-score {z_str}), a statistically "
            f"significant spike dominated by {category} errors."
        )
    else:
        qualifier = (
            "limited surrounding data"
            if confidence == "MEDIUM"
            else "no comparable surrounding data"
        )
        baseline_str = f"{baseline:.1f}" if baseline is not None else "unavailable"
        reason = (
            f"{error_count} errors detected with {qualifier} "
            f"(baseline: {baseline_str}). "
            f"Interpret with caution -- confidence is {confidence}."
        )

    return {
        "error_count": error_count,
        "local_baseline": baseline,
        "deviation_pct": deviation_pct,
        "z_score": z_score,
        "confidence": confidence,
        "dominant_pattern": category,
        "severity": incident_card["severity"],
        "reason": reason,
    }
