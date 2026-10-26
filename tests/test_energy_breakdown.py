"""Checks the energy waterfall adds up exactly and tells the right story (Phase W3).

Run with:   pytest
"""

import pandas as pd
import pytest

from engine import config
from engine.energy_breakdown import PART_NAMES
from engine.metrics import load_metrics


@pytest.fixture(scope="module")
def breakdown():
    """Load the daily waterfall table, the daily plant table and the breakdown metrics once."""
    for path in [config.ENERGY_BREAKDOWN_FILE, config.DAILY_PLANT_FILE, config.WEATHER_DAILY_FILE]:
        if not path.exists():
            pytest.skip(f"{path.name} not found — run: python -m engine.energy_breakdown")
    return {"days": pd.read_parquet(config.ENERGY_BREAKDOWN_FILE),
            "plant": pd.read_parquet(config.DAILY_PLANT_FILE),
            "weather": pd.read_parquet(config.WEATHER_DAILY_FILE),
            "metrics": load_metrics()["breakdown"]}


def test_every_day_adds_up_to_actual(breakdown):
    """Potential − clouds − heat − faults − not measured − other = actual, for every plant and day."""
    days = breakdown["days"]
    rebuilt = days["clear_sky_potential_kwh"] - days[list(PART_NAMES)].sum(axis=1)
    assert (rebuilt - days["actual_kwh"]).abs().max() < 0.1   # rounding to 2 decimals only


def test_period_totals_add_up(breakdown):
    """The same is true for each plant's whole-period totals in metrics.json."""
    for info in [*breakdown["metrics"]["by_plant"].values(), breakdown["metrics"]["total"]]:
        rebuilt = info["clear_sky_potential_kwh"] - sum(info[part] for part in PART_NAMES)
        assert rebuilt == pytest.approx(info["actual_kwh"], abs=1.0)


def test_actual_and_fault_loss_match_the_loss_step(breakdown):
    """Actual energy and fault loss are the SAME numbers as Phase 6 (not recomputed differently)."""
    merged = breakdown["days"].merge(breakdown["plant"], on=["plant", "date"], suffixes=("", "_phase6"))
    assert len(merged) == len(breakdown["days"]) == 68
    assert (merged["actual_kwh"] - merged["actual_kwh_phase6"]).abs().max() < 0.01
    assert (merged["fault_loss_kwh"] - merged["fault_loss_kwh_phase6"]).abs().max() < 0.01


def test_natural_vs_fixable_labels(breakdown):
    """Clouds and heat are natural, faults are fixable — the key pitch point."""
    kind = breakdown["metrics"]["kind"]
    assert kind["clouds"] == kind["heat"] == "natural"
    assert kind["faults"] == "fixable"


def test_cloudy_day_has_bigger_cloud_loss_than_sunny_day(breakdown):
    """The sunniest day of each plant loses far less to clouds than its cloudiest day."""
    days, weather = breakdown["days"], breakdown["weather"]
    for plant in config.PLANTS:
        sky = weather[(weather["plant"] == plant) & (weather["coverage_pct"] >= config.SKY_MIN_COVERAGE_PCT)]
        sunny = sky.loc[sky["sunshine_score"].idxmax(), "date"]
        cloudy = sky.loc[sky["sunshine_score"].idxmin(), "date"]
        loss = days[days["plant"] == plant].set_index("date")["cloud_loss_kwh"]
        assert loss[cloudy] > 3 * loss[sunny]


def test_clear_sky_potential_check_against_physics_model(breakdown):
    """Our 25 °C 'power per unit sunlight' agrees with the Phase 3 physics model within 5%."""
    for info in breakdown["metrics"]["by_plant"].values():
        assert info["power_per_sunlight_at_25c_kw"] == pytest.approx(info["physics_model_cross_check_kw"], rel=0.05)


def test_other_is_small(breakdown):
    """The unexplained remainder is a small share of the potential (the parts really explain the energy)."""
    for info in breakdown["metrics"]["by_plant"].values():
        assert abs(info["pct_of_potential"]["other"]) < 2
