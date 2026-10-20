"""Checks that the loss numbers add up everywhere (Phase 6).

Run with:   pytest
"""

import pandas as pd
import pytest

from engine import config
from engine.metrics import load_metrics


@pytest.fixture(scope="module")
def outputs():
    """Load alerts, daily tables and the losses section once."""
    for path in [config.ALERTS_FILE, config.DAILY_PLANT_FILE, config.DAILY_INVERTER_FILE]:
        if not path.exists():
            pytest.skip(f"{path.name} not found — run: python -m engine.losses")
    return {"alerts": pd.read_parquet(config.ALERTS_FILE),
            "plant": pd.read_parquet(config.DAILY_PLANT_FILE),
            "inverter": pd.read_parquet(config.DAILY_INVERTER_FILE),
            "losses": load_metrics()["losses"]}


def test_money_is_energy_times_tariff(outputs):
    """Every ₹ value must equal kWh × tariff (rounded to whole rupees)."""
    alerts = outputs["alerts"]
    expected_inr = (alerts["energy_loss_kwh"] * config.TARIFF_INR_PER_KWH).round(0)
    assert (alerts["money_loss_inr"] - expected_inr).abs().max() < 1


def test_data_gaps_have_no_confirmed_loss(outputs):
    """Gaps are 'at risk', never 'lost'; other faults are never 'at risk'."""
    alerts = outputs["alerts"]
    gaps = alerts["fault_type"] == "DATA_GAP"
    assert (alerts.loc[gaps, "energy_loss_kwh"] == 0).all()
    assert (alerts.loc[~gaps, "energy_at_risk_kwh"] == 0).all()


def test_totals_add_up(outputs):
    """Total = sum by fault type = sum by plant = sum of daily tables = sum of alerts."""
    losses, alerts = outputs["losses"], outputs["alerts"]
    total = losses["total"]["fault_loss_kwh"]
    by_type = sum(v["fault_loss_kwh"] for v in losses["by_fault_type"].values())
    by_plant = sum(v["fault_loss_kwh"] for v in losses["by_plant"].values())
    for value in [by_type, by_plant, outputs["plant"]["fault_loss_kwh"].sum(), alerts["energy_loss_kwh"].sum()]:
        assert value == pytest.approx(total, abs=1.0)


def test_inverter_days_add_up_to_plant_days(outputs):
    """Adding up inverters for a day gives the plant's numbers for that day."""
    summed = outputs["inverter"].groupby(["plant", "date"])[["actual_kwh", "expected_kwh"]].sum()
    plant = outputs["plant"].set_index(["plant", "date"])[["actual_kwh", "expected_kwh"]]
    assert (summed - plant).abs().max().max() < 1.0


def test_projection_is_simple_scaling(outputs):
    """Projected annual loss = period loss ÷ days × 365."""
    losses = outputs["losses"]
    expected = losses["total"]["fault_loss_kwh"] / losses["days"] * config.DAYS_PER_YEAR
    assert losses["total"]["projected_annual_fault_loss_kwh"] == pytest.approx(expected, abs=1.0)
