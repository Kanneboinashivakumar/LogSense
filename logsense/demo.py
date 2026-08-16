"""Demo runner: analyze each test log file and print results with confidence tiers.

Usage: python -m logsense.demo
"""

from __future__ import annotations

import sys
from pathlib import Path

from logsense.analysis import detect_spikes, find_peak_hour
from logsense.bucketing import bucket_by_hour
from logsense.incident import build_evidence_panel, build_incident_card
from logsense.parser import parse_logs
from logsense.report import generate_report


def analyze_file(filepath: Path) -> None:
    """Run the full analysis pipeline on a single log file and print results."""
    print(f"\n{'=' * 70}")
    print(f"  FILE: {filepath.name}")
    print(f"{'=' * 70}")

    raw_text = filepath.read_text(encoding="utf-8")
    parse_result = parse_logs(raw_text)

    print(f"\n  Parsed entries: {len(parse_result.entries)}")
    if parse_result.warnings:
        print(f"  Warnings ({len(parse_result.warnings)}):")
        for w in parse_result.warnings:
            print(f"    [!] {w}")

    if not parse_result.entries:
        print("  No valid entries to analyze.")
        return

    buckets = bucket_by_hour(parse_result.entries)
    peak_hour = find_peak_hour(buckets)
    spikes = detect_spikes(buckets)

    # Print the full report
    report = generate_report(buckets, peak_hour, spikes)
    print(report)

    # Print spike details with confidence tiers
    flagged = [s for s in spikes if s.is_spike]
    if flagged:
        print("\n  SPIKE DETAILS WITH CONFIDENCE TIERS:")
        print(f"  {'-' * 60}")
        for spike in flagged:
            card = build_incident_card(spike.hour, buckets, spike)
            panel = build_evidence_panel(card, spike.z_score)

            print(f"\n  Hour: {spike.hour}")
            print(f"    Confidence : {spike.confidence}")
            print(f"    Error Count: {spike.error_count}")
            print(f"    Baseline   : {spike.baseline}")
            print(f"    Deviation  : {spike.deviation_pct}")
            print(f"    Z-Score    : {spike.z_score}")
            print(f"    Severity   : {card['severity']}")
            print(f"    Pattern    : {card['category']}")
            print(f"    Reason     : {panel['reason']}")
    else:
        print("\n  No spikes detected -- all hours within normal range.")


def main() -> None:
    """Analyze the three requested test files."""
    test_data_dir = Path(__file__).resolve().parent.parent / "test_data"

    files_to_analyze = [
        "sample_clean_spike.log",
        "sample_tiny.log",
        "sample_no_spike.log",
    ]

    for filename in files_to_analyze:
        filepath = test_data_dir / filename
        if not filepath.exists():
            print(f"ERROR: {filepath} not found", file=sys.stderr)
            continue
        analyze_file(filepath)

    print(f"\n{'=' * 70}")
    print("  Demo complete.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
