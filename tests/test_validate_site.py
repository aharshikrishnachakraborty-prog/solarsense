"""Checks the Solar Site Planner accuracy tests (engine/validate_site.py). No internet: PVGIS and NASA are faked.

Run with:   pytest
"""

import pandas as pd
import pytest

from engine import config, validate_site


def test_backtest_is_an_honest_time_split():
    """Tuned on early days only, scored on later unseen days; the daily method stays close to the real energy."""
    if not config.ENERGY_BREAKDOWN_FILE.exists():
        pytest.skip("Run the pipeline first (python run_all.py)")
    result = validate_site.backtest()
    start = result["test_period"].split(" to ")[0]
    assert result["train_days"] > 0 and result["test_days"] > 0
    assert start > "2020-06-01"   # test days are the LAST days of the data
    assert result["planner"]["daily_error_pct"] < 10
    assert abs(result["planner"]["total_error_pct"]) < 10


def test_gap_splits_into_sunlight_and_maths(monkeypatch):
    """(1 + sunlight gap) × (1 + maths gap) = 1 + total gap — the split explains the whole difference."""
    years = pd.DataFrame({"yield_kwh_per_kw": [1300.0, 1400.0], "sunlight_kwh_m2": [1700.0, 1800.0]},
                         index=pd.Index([2021, 2022], name="year"))
    reference = {"yield_kwh_per_kw": 1400.0, "sunlight_kwh_m2": 1900.0, "weather_data": "fake", "loss_pct": 17.44,
                 "reflection_loss_pct": 3.0, "heat_loss_pct": 10.0}
    monkeypatch.setattr(validate_site, "yearly_nasa", lambda lat, lon, cal: years)
    monkeypatch.setattr(validate_site, "pvgis", lambda lat, lon: reference)
    city = validate_site.compare_city({"name": "Test", "lat": 20.0, "lon": 80.0}, cal={})
    combined = (1 + city["sunlight_gap_pct"] / 100) * (1 + city["maths_gap_pct"] / 100) - 1
    assert 100 * combined == pytest.approx(city["total_gap_pct"], abs=0.2)
    assert city["year_spread_pct"] == pytest.approx(100 * 100 / 1350, abs=0.1)


def test_accuracy_results_are_saved_for_the_page():
    """metrics.json has the backtest, the 3 preset cities and the summary sentence the page shows."""
    from engine.metrics import load_metrics
    accuracy = load_metrics().get("site_accuracy")
    if not accuracy:
        pytest.skip("Run python -m engine.validate_site first")
    assert set(accuracy["cities"]) == {city["name"] for city in config.SITE_PRESETS}
    assert "PVGIS" in accuracy["summary"] and "Backtest" in accuracy["summary"]
