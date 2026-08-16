"""LogSense plain-text report generator.

Produces a human-readable report containing:
1. Hour-wise error breakdown
2. Peak error hour identification
3. Spike alerts with confidence and severity

This report is designed to satisfy the problem statement requirements
even with zero UI — it's the canonical textual answer.
"""

from __future__ import annotations

from typing import Optional

from logsense.analysis import SpikeResult, classify_severity
from logsense.bucketing import HourBucket

# Width of the separator line in the report
_SEPARATOR_WIDTH: int = 60


def generate_report(
    buckets: dict[str, HourBucket],
    peak_hour: Optional[str],
    spikes: list[SpikeResult],
) -> str:
    """Generate a formatted plain-text analysis report.

    The report contains three mandatory sections that directly answer
    the problem statement:

    1. **Hour-wise Error Breakdown** — a table of every hour showing
       total entries, errors, and warnings.
    2. **Peak Error Hour** — the single hour with the most errors.
    3. **Spike Alerts** — every detected spike with its severity,
       confidence tier, and key statistics.

    Args:
        buckets: Hourly buckets from ``bucket_by_hour``.
        peak_hour: The hour key from ``find_peak_hour``, or ``None``.
        spikes: All ``SpikeResult`` objects from ``detect_spikes``.

    Returns:
        A multi-line formatted string suitable for terminal output.
    """
    lines: list[str] = []
    sep = "=" * _SEPARATOR_WIDTH

    # ── Header ────────────────────────────────────────────────────────
    lines.append(sep)
    lines.append("  LOGSENSE -- Log Incident Analysis Report")
    lines.append(sep)
    lines.append("")

    # ── Section 1: Hour-wise error breakdown ──────────────────────────
    lines.append("HOUR-WISE ERROR BREAKDOWN")
    lines.append("-" * _SEPARATOR_WIDTH)
    lines.append(f"{'Hour':<22} {'Total':>6} {'Errors':>7} {'Warnings':>9}")
    lines.append("-" * _SEPARATOR_WIDTH)

    for hour in sorted(buckets.keys()):
        b = buckets[hour]
        lines.append(
            f"{hour:<22} {b['total_count']:>6} "
            f"{b['error_count']:>7} {b['warning_count']:>9}"
        )

    lines.append("")

    # ── Section 2: Peak error hour ────────────────────────────────────
    lines.append("PEAK ERROR HOUR")
    lines.append("-" * _SEPARATOR_WIDTH)

    if peak_hour is not None:
        peak_errors = buckets[peak_hour]["error_count"]
        lines.append(f"  {peak_hour}  ({peak_errors} errors)")
    else:
        lines.append("  No data available.")

    lines.append("")

    # ── Section 3: Spike alerts ───────────────────────────────────────
    lines.append("SPIKE ALERTS")
    lines.append("-" * _SEPARATOR_WIDTH)

    spike_hours = [
        s for s in spikes
        if s.is_spike and classify_severity(s.deviation_pct) in ("Warning", "Critical")
    ]

    if not spike_hours:
        lines.append("  No spikes detected -- traffic appears normal.")
    else:
        for spike in spike_hours:
            severity = classify_severity(spike.deviation_pct)
            lines.append(f"  [!] SPIKE: {spike.hour}")
            lines.append(f"    Severity   : {severity}")
            lines.append(f"    Confidence : {spike.confidence}")
            lines.append(f"    Errors     : {spike.error_count}")

            if spike.baseline is not None:
                lines.append(f"    Baseline   : {spike.baseline:.1f}")

            if spike.deviation_pct is not None:
                dev_str = (
                    "INF" if spike.deviation_pct == float("inf")
                    else f"{spike.deviation_pct:.1f}%"
                )
                lines.append(f"    Deviation  : {dev_str}")

            if spike.z_score is not None:
                z_str = (
                    "INF" if spike.z_score == float("inf")
                    else f"{spike.z_score:.2f}"
                )
                lines.append(f"    Z-score    : {z_str}")

            lines.append("")

    lines.append(sep)

    return "\n".join(lines)
