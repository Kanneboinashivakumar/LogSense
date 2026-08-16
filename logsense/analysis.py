"""LogSense statistical analysis.

Implements peak-hour detection, baseline deviation calculation, and
confidence-tiered spike detection using z-scores (when enough neighbors
are available) or simpler percentage deviation (when data is sparse).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from logsense.bucketing import HourBucket

# ── Severity thresholds (percentage deviation from baseline) ──────────
SEVERITY_NORMAL_UPPER: float = 50.0    # <50 % → Normal
SEVERITY_WARNING_UPPER: float = 150.0  # 50-150 % → Warning  ;  >150 % → Critical

# ── Spike detection thresholds ────────────────────────────────────────
Z_SCORE_SPIKE_THRESHOLD: float = 2.0         # flag if z-score > 2
MIN_NEIGHBORS_FOR_ZSCORE: int = 3            # need ≥3 neighbors for z-score
PERCENT_DEVIATION_SPIKE_THRESHOLD: float = 100.0  # 100% above baseline when using fallback


@dataclass
class SpikeResult:
    """Result of spike detection for a single hour.

    Attributes:
        hour: The bucket key (``YYYY-MM-DD HH:00``).
        is_spike: Whether this hour was flagged as a spike.
        error_count: Raw error count in this hour.
        baseline: Computed local baseline (mean of neighbors), or None.
        deviation_pct: Percentage deviation from baseline, or None.
        z_score: Z-score relative to neighbors, or None when insufficient data.
        confidence: ``HIGH``, ``MEDIUM``, or ``LOW``.
    """

    hour: str
    is_spike: bool
    error_count: int
    baseline: Optional[float]
    deviation_pct: Optional[float]
    z_score: Optional[float]
    confidence: str


def find_peak_hour(buckets: dict[str, HourBucket]) -> Optional[str]:
    """Return the hour key with the highest error count.

    Args:
        buckets: Hourly buckets from ``bucket_by_hour``.

    Returns:
        The bucket key string for the peak hour, or ``None`` if there
        are no buckets.
    """
    if not buckets:
        return None

    return max(buckets, key=lambda k: buckets[k]["error_count"])


def calculate_baseline_deviation(
    buckets: dict[str, HourBucket],
) -> dict[str, dict[str, Optional[float]]]:
    """Compute local baseline and deviation for every hour.

    The local baseline for a given hour is the mean error count of its
    *neighboring* hours (i.e. all hours except itself).  For datasets
    with many hours this is effectively a leave-one-out mean.

    Args:
        buckets: Hourly buckets from ``bucket_by_hour``.

    Returns:
        A dict keyed by hour containing ``baseline`` and ``deviation_pct``.
    """
    hours = list(buckets.keys())
    result: dict[str, dict[str, Optional[float]]] = {}

    for hour in hours:
        neighbors = [buckets[h]["error_count"] for h in hours if h != hour]

        if not neighbors:
            result[hour] = {"baseline": None, "deviation_pct": None}
            continue

        baseline = sum(neighbors) / len(neighbors)

        if baseline == 0:
            deviation_pct = float(buckets[hour]["error_count"]) * 100.0 if buckets[hour]["error_count"] > 0 else 0.0
        else:
            deviation_pct = (
                (buckets[hour]["error_count"] - baseline) / baseline
            ) * 100.0

        result[hour] = {"baseline": baseline, "deviation_pct": deviation_pct}

    return result


def _get_neighbor_error_counts(
    hours: list[str],
    index: int,
    buckets: dict[str, HourBucket],
    excluded_indices: frozenset[int] = frozenset(),
) -> list[int]:
    """Return error counts for the immediate neighboring hours.

    Neighbors are the hours directly adjacent in chronological order
    (up to 3 on each side, for a max of 6 neighbors).  This gives a
    *local* context window rather than comparing against the global mean.

    Hours at indices listed in ``excluded_indices`` are skipped — this
    allows a second detection pass to exclude already-identified spikes
    so they don't inflate the baseline for nearby hours.

    Args:
        hours: Sorted list of hour keys.
        index: Index of the hour being evaluated.
        buckets: The full bucket dict.
        excluded_indices: Set of hour indices to skip (already-detected spikes).

    Returns:
        A list of neighbor error counts (may be empty at dataset edges).
    """
    max_neighbor_distance: int = 3
    neighbors: list[int] = []

    for offset in range(-max_neighbor_distance, max_neighbor_distance + 1):
        if offset == 0:
            continue
        neighbor_idx = index + offset
        if 0 <= neighbor_idx < len(hours) and neighbor_idx not in excluded_indices:
            neighbors.append(buckets[hours[neighbor_idx]]["error_count"])

    return neighbors


def _evaluate_hour(
    hour: str,
    idx: int,
    hours: list[str],
    buckets: dict[str, HourBucket],
    excluded_indices: frozenset[int] = frozenset(),
) -> SpikeResult:
    """Evaluate a single hour for spike detection.

    Extracted to support multi-pass detection where already-identified
    spikes are excluded from the neighbor baseline.

    Args:
        hour: The bucket key being evaluated.
        idx: Index of this hour in the sorted hours list.
        hours: Sorted list of all hour keys.
        buckets: The full bucket dict.
        excluded_indices: Indices of hours to exclude from neighbor calculations.

    Returns:
        A ``SpikeResult`` for this hour.
    """
    error_count = buckets[hour]["error_count"]
    neighbors = _get_neighbor_error_counts(hours, idx, buckets, excluded_indices)

    # ── No usable neighbors ───────────────────────────────────────
    if len(neighbors) == 0:
        return SpikeResult(
            hour=hour,
            is_spike=error_count > 0,
            error_count=error_count,
            baseline=None,
            deviation_pct=None,
            z_score=None,
            confidence="LOW",
        )

    neighbor_mean = sum(neighbors) / len(neighbors)

    # ── Baseline is zero ──────────────────────────────────────────
    if neighbor_mean == 0:
        is_spike = error_count > 0
        return SpikeResult(
            hour=hour,
            is_spike=is_spike,
            error_count=error_count,
            baseline=0.0,
            deviation_pct=float("inf") if is_spike else 0.0,
            z_score=None,
            confidence="MEDIUM",
        )

    deviation_pct = ((error_count - neighbor_mean) / neighbor_mean) * 100.0

    # ── Enough neighbors for z-score (>=3) ────────────────────────
    if len(neighbors) >= MIN_NEIGHBORS_FOR_ZSCORE:
        variance = sum(
            (n - neighbor_mean) ** 2 for n in neighbors
        ) / len(neighbors)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            z_score = float("inf") if error_count > neighbor_mean else 0.0
        else:
            z_score = (error_count - neighbor_mean) / std_dev

        is_spike = z_score > Z_SCORE_SPIKE_THRESHOLD
        return SpikeResult(
            hour=hour,
            is_spike=is_spike,
            error_count=error_count,
            baseline=neighbor_mean,
            deviation_pct=deviation_pct,
            z_score=z_score,
            confidence="HIGH",
        )
    else:
        # ── 1-2 neighbors: percentage-deviation fallback ──────────
        is_spike = deviation_pct > PERCENT_DEVIATION_SPIKE_THRESHOLD
        return SpikeResult(
            hour=hour,
            is_spike=is_spike,
            error_count=error_count,
            baseline=neighbor_mean,
            deviation_pct=deviation_pct,
            z_score=None,
            confidence="MEDIUM",
        )


# Maximum number of iterative spike-exclusion passes
_MAX_DETECTION_PASSES: int = 5


def detect_spikes(buckets: dict[str, HourBucket]) -> list[SpikeResult]:
    """Detect error spikes using confidence-tiered logic with iterative refinement.

    Uses a multi-pass approach: the first pass detects obvious spikes,
    then subsequent passes re-evaluate non-spike hours after excluding
    the already-detected spikes from the neighbor baseline.  This
    prevents a large spike from inflating the baseline of a neighboring
    spike and masking it.

    The confidence tier depends on how much neighboring data is available:

    - **HIGH** (>=3 neighbors): Compute mean and std-dev of neighbor
      error counts, then flag as spike if the z-score exceeds the
      threshold (currently 2.0).
    - **MEDIUM** (1-2 neighbors, or baseline == 0 with nonzero errors):
      Fall back to plain percentage deviation from the available
      baseline.  No z-score is computed because the sample is too small
      for it to be statistically meaningful.
    - **LOW** (no usable neighbors): Report the raw count but never
      fabricate a baseline.  The hour is still flagged if it has errors,
      since we can't prove it *isn't* anomalous, but with low confidence.

    Args:
        buckets: Hourly buckets from ``bucket_by_hour``.

    Returns:
        A list of ``SpikeResult`` for every hour, including non-spike
        hours (``is_spike=False``).
    """
    hours = sorted(buckets.keys())

    if not hours:
        return []

    # First pass: detect with no exclusions
    results: dict[str, SpikeResult] = {}
    for idx, hour in enumerate(hours):
        results[hour] = _evaluate_hour(hour, idx, hours, buckets)

    # Iterative refinement: exclude detected spikes and re-evaluate.
    # Second-pass spikes must have substantially more errors than the
    # recalculated baseline to avoid promoting borderline hours.
    REFINEMENT_MIN_ERROR_RATIO: float = 5.0

    for _ in range(_MAX_DETECTION_PASSES):
        spike_indices = frozenset(
            idx for idx, hour in enumerate(hours) if results[hour].is_spike
        )

        new_spikes_found = False

        for idx, hour in enumerate(hours):
            if results[hour].is_spike:
                continue  # Already a spike, skip

            new_result = _evaluate_hour(
                hour, idx, hours, buckets, excluded_indices=spike_indices
            )

            # Only promote if the recalculated result says spike AND
            # the error count is substantially above the new baseline.
            # This prevents borderline cases (e.g. 3 errors vs baseline
            # 1.8) from being falsely promoted just because excluding a
            # nearby large spike tightened the baseline.
            if new_result.is_spike and not results[hour].is_spike:
                baseline = new_result.baseline or 0.0
                if baseline == 0 or new_result.error_count >= baseline * REFINEMENT_MIN_ERROR_RATIO:
                    results[hour] = new_result
                    new_spikes_found = True

        if not new_spikes_found:
            break  # No new spikes discovered, converged

    return [results[hour] for hour in hours]


def classify_severity(deviation_pct: Optional[float]) -> str:
    """Map a deviation percentage to a human-readable severity label.

    Thresholds:
    - ``< 50%``  → Normal
    - ``50–150%`` → Warning
    - ``> 150%``  → Critical
    - ``None`` (no baseline available) → Normal (safe default)

    Args:
        deviation_pct: The percentage deviation from baseline, or None.

    Returns:
        One of ``"Normal"``, ``"Warning"``, or ``"Critical"``.
    """
    if deviation_pct is None:
        return "Normal"

    if deviation_pct < SEVERITY_NORMAL_UPPER:
        return "Normal"
    if deviation_pct <= SEVERITY_WARNING_UPPER:
        return "Warning"
    return "Critical"
