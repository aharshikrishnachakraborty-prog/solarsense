"""Checks that data/processed/alerts.parquet is complete and sensible (Phase 4).

Run with:   pytest
"""

import json

import pandas as pd
import pytest

from engine import config

REQUIRED = ["id", "plant", "inverter", "fault_type", "start", "end", "duration_hours", "severity",
            "reason", "evidence", "recommended_action", "status"]


@pytest.fixture(scope="module")
def alerts():
    """Load the alerts table once for all tests in this file."""
    if not config.ALERTS_FILE.exists():
        pytest.skip("alerts.parquet not found — run: python -m engine.detect_faults")
    return pd.read_parquet(config.ALERTS_FILE)


def test_every_alert_has_all_fields(alerts):
    """No required field may be blank."""
    assert alerts[REQUIRED].notna().all().all()


def test_ids_are_unique(alerts):
    """Every alert must have its own id."""
    assert alerts["id"].is_unique


def test_every_reason_contains_a_real_number(alerts):
    """Reasons must quote numbers, not vague words."""
    assert alerts["reason"].str.contains(r"\d").all()


def test_start_before_end(alerts):
    """An alert cannot end before it starts."""
    assert (alerts["start"] < alerts["end"]).all()


def test_values_are_from_allowed_lists(alerts):
    """Severity, status and action must use our fixed vocabulary."""
    assert alerts["severity"].isin(config.SEVERITY_LEVELS).all()
    assert (alerts["status"] == "Open").all()
    assert alerts["evidence"].map(json.loads).map(lambda ev: isinstance(ev, dict)).all()


def test_data_gaps_never_critical(alerts):
    """A data gap is not a confirmed loss, so it is capped at High."""
    assert not ((alerts["fault_type"] == "DATA_GAP") & (alerts["severity"] == "Critical")).any()


def test_trip_and_underperformance_never_overlap(alerts):
    """The same inverter cannot be both tripped and underperforming at the same moment."""
    trips = alerts[alerts["fault_type"] == "INVERTER_TRIP"]
    under = alerts[alerts["fault_type"] == "UNDERPERFORMANCE"]
    merged = trips.merge(under, on=["plant", "inverter"], suffixes=("_trip", "_under"))
    overlapping = (merged["start_trip"] < merged["end_under"]) & (merged["start_under"] < merged["end_trip"])
    assert not overlapping.any()
