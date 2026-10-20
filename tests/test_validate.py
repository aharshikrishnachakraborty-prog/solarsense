"""Checks for the injected-fault validation (Phase 7).

Run with:   pytest
"""

import numpy as np
import pytest

from engine import config
from engine.fault_injection import inject_one, load_test_data, pick_days
from engine.metrics import load_metrics


@pytest.fixture(scope="module")
def test_data():
    """Test-day rows and clean inverter-days."""
    if not config.ALERTS_FILE.exists():
        pytest.skip("Run the pipeline first (python -m engine.detect_faults)")
    return load_test_data()


def test_trip_injection_only_changes_its_window(test_data):
    """A trip sets output to 0 inside its window and touches nothing else."""
    test, clean = test_data
    table = test.copy()
    plant, inverter, date = sorted(clean)[0]
    record = inject_one(table, "trip", plant, inverter, date, np.random.default_rng(0))
    inside = ((table["plant"] == plant) & (table["inverter"] == inverter)
              & (table["timestamp"] >= record["start"]) & (table["timestamp"] < record["end"]))
    assert (table.loc[inside, "ac_kw"].dropna() == 0).all()
    assert table.loc[~inside, "ac_kw"].equals(test.loc[~inside, "ac_kw"])


def test_injections_are_reproducible(test_data):
    """The same seed must give exactly the same injected faults."""
    test, clean = test_data
    a = [inject_one(test.copy(), "underperformance", *p, np.random.default_rng(1))
         for p in pick_days(clean, np.random.default_rng(1))[:3]]
    b = [inject_one(test.copy(), "underperformance", *p, np.random.default_rng(1))
         for p in pick_days(clean, np.random.default_rng(1))[:3]]
    assert a == b


def test_no_two_injections_share_a_plant_day(test_data):
    """Faults in one run never overlap in time within a plant (keeps the peer median fair)."""
    _, clean = test_data
    picks = pick_days(clean, np.random.default_rng(2))
    assert len({(p, d) for p, _, d in picks}) == len(picks)


def test_validation_results_are_honest():
    """Results exist and are not 'too good': at least one fault type is below 100% recall."""
    validation = load_metrics().get("validation")
    if validation is None:
        pytest.skip("Run: python -m engine.validate")
    recalls = [v["recall_pct"] for v in validation["by_fault"].values()]
    assert all(0 <= r <= 100 for r in recalls)
    assert min(recalls) < 100
