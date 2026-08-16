"""Shared pytest fixtures for LogSense test suite.

All test data files live in ``test_data/`` and are loaded once per
session (they're small files so this is fine for memory).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Root of the test_data directory, relative to the project root
_TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the absolute path to the test_data directory."""
    assert _TEST_DATA_DIR.is_dir(), f"test_data directory not found at {_TEST_DATA_DIR}"
    return _TEST_DATA_DIR


@pytest.fixture(scope="session")
def clean_spike_text(test_data_dir: Path) -> str:
    """Raw text of sample_clean_spike.log (one obvious spike at 15:00)."""
    return (test_data_dir / "sample_clean_spike.log").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def no_spike_text(test_data_dir: Path) -> str:
    """Raw text of sample_no_spike.log (stable traffic, no anomaly)."""
    return (test_data_dir / "sample_no_spike.log").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def multi_spike_text(test_data_dir: Path) -> str:
    """Raw text of sample_multi_spike.log (two separate spikes)."""
    return (test_data_dir / "sample_multi_spike.log").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def tiny_text(test_data_dir: Path) -> str:
    """Raw text of sample_tiny.log (under 5 lines)."""
    return (test_data_dir / "sample_tiny.log").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def malformed_text(test_data_dir: Path) -> str:
    """Raw text of sample_malformed.log (mixed valid/garbage lines)."""
    return (test_data_dir / "sample_malformed.log").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def empty_text(test_data_dir: Path) -> str:
    """Raw text of sample_empty.log (empty file)."""
    return (test_data_dir / "sample_empty.log").read_text(encoding="utf-8")
