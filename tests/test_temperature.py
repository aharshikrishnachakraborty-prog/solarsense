"""Checks the temperature effect on power: coefficient, heat loss and hot hours (Phase W2).

Run with:   pytest
"""

import pandas as pd
import pytest

from engine import config
from engine.metrics import load_metrics
from engine.weather_temperature import coefficient_from_sums, heat_loss_15min


@pytest.fixture(scope="module")
def weather():
    """Load the 15-minute and daily weather tables and the temperature metrics once."""
    for path in [config.WEATHER_15MIN_FILE, config.WEATHER_DAILY_FILE]:
        if not path.exists():
            pytest.skip(f"{path.name} not found — run: python -m engine.weather")
    metrics = load_metrics()
    if "temperature" not in metrics:
        pytest.skip("no 'temperature' metrics — run: python -m engine.weather")
    return {"readings": pd.read_parquet(config.WEATHER_15MIN_FILE),
            "daily": pd.read_parquet(config.WEATHER_DAILY_FILE),
            "metrics": metrics["temperature"]}


def test_coefficient_is_negative_and_believable(weather):
    """Hot panels make LESS power: coefficient < 0, inside its 95% range and the believable range."""
    believable_low, believable_high = config.BELIEVABLE_TEMP_COEF_RANGE
    for info in weather["metrics"]["by_plant"].values():
        low, high = info["ci95_pct_per_c"]
        assert info["coefficient_pct_per_c"] < 0
        assert low <= info["coefficient_pct_per_c"] <= high
        assert believable_low <= info["coefficient_used_pct_per_c"] <= believable_high


def test_heat_loss_is_never_negative_and_zero_when_cool(weather):
    """Heat loss ≥ 0 always, and exactly 0 when the panel is at or below 25 °C."""
    readings = weather["readings"]
    assert (readings["heat_loss_kw"] >= 0).all()
    cool = readings["module_temp"] <= config.REFERENCE_PANEL_TEMP_C
    assert (readings.loc[cool, "heat_loss_kw"] == 0).all()


def test_daily_heat_loss_adds_up(weather):
    """Daily kWh = sum of 15-minute kW × 0.25 h, and ₹ = kWh × tariff."""
    readings, daily = weather["readings"], weather["daily"].copy()
    from_readings = readings.groupby(["plant", readings["date"].astype(str)])["heat_loss_kw"].sum() * config.INTERVAL_HOURS
    daily = daily.set_index(["plant", "date"])
    assert (daily["heat_loss_kwh"] - from_readings.reindex(daily.index)).abs().max() < 0.1
    assert (daily["heat_loss_inr"] - daily["heat_loss_kwh"] * config.TARIFF_INR_PER_KWH).abs().max() < 1


def test_hot_hours_match_threshold(weather):
    """Hot hours per day = readings at/above the threshold × 0.25 h."""
    readings, daily = weather["readings"], weather["daily"]
    hot = (readings["module_temp"] >= config.HOT_MODULE_TEMP_C)
    assert (readings["is_hot_hour"] == hot).all()
    from_readings = hot.groupby([readings["plant"], readings["date"].astype(str)]).sum() * config.INTERVAL_HOURS
    assert from_readings.sum() == pytest.approx(daily["hot_hours"].sum())


def test_panels_heat_up_with_sunlight(weather):
    """More sunlight → hotter panels than the air (positive slope, decent straight-line fit)."""
    for info in weather["metrics"]["by_plant"].values():
        heating = info["panel_heating"]
        assert heating["heating_c_per_kw_m2"] > 0
        assert heating["r2"] > 0.5


def test_line_fit_from_sums_matches_known_line():
    """The running-sums fit recovers a made-up line: efficiency 1.0 at 25 °C falling 0.004 per °C = −0.4 %/°C."""
    temps = pd.Series([25.0, 35.0, 45.0, 55.0, 65.0])
    x = temps - 25
    y = 1.0 - 0.004 * x
    coefficient = coefficient_from_sums(len(x), x.sum(), y.sum(), (x * x).sum(), (x * y).sum())
    assert coefficient == pytest.approx(-0.4)


def test_heat_loss_formula_on_one_reading():
    """At 50 °C with −0.4 %/°C, a model expecting 900 kW → 25 °C power 1,000 kW → heat loss 100 kW."""
    rows = pd.DataFrame({"plant": [1], "timestamp": [pd.Timestamp("2020-05-20 12:00")], "expected_kw": [900.0],
                         "ac_kw": [900.0], "module_temp": [50.0]})
    result = heat_loss_15min(rows, {1: -0.4})
    assert result["power_at_25c_kw"].iloc[0] == pytest.approx(1000.0)
    assert result["heat_loss_kw"].iloc[0] == pytest.approx(100.0)
