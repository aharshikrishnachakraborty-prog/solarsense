"""Checks that the sky labels from sunlight make sense (Phase W1).

Run with:   pytest
"""

import pandas as pd
import pytest

from engine import config
from engine.metrics import load_metrics
from engine.weather_text import describe_day


@pytest.fixture(scope="module")
def weather():
    """Load the 15-minute table, the daily table and the weather metrics once."""
    for path in [config.WEATHER_15MIN_FILE, config.WEATHER_DAILY_FILE]:
        if not path.exists():
            pytest.skip(f"{path.name} not found — run: python -m engine.weather")
    return {"readings": pd.read_parquet(config.WEATHER_15MIN_FILE),
            "daily": pd.read_parquet(config.WEATHER_DAILY_FILE),
            "metrics": load_metrics()["weather"]}


def test_one_reading_per_plant_and_slot(weather):
    """34 days × 96 readings per plant, no duplicates (weather is per plant, not per inverter)."""
    readings = weather["readings"]
    assert not readings.duplicated(["plant", "timestamp"]).any()
    assert readings.groupby("plant").size().eq(34 * config.READINGS_PER_DAY).all()


def test_clear_sky_curve_is_a_daytime_bell(weather):
    """Clear-sky sunlight is ~0 at night and peaks around midday (11:00–13:30)."""
    for _, plant in weather["readings"].groupby("plant"):
        curve = plant.groupby("slot")["clear_sky_irr"].first()
        assert curve.loc[0:16].max() < 0.01          # 00:00–04:00
        assert curve.loc[84:].max() < 0.01           # 21:00–23:45
        assert 44 <= curve.idxmax() <= 54            # peak between 11:00 and 13:30


def test_csi_stays_in_range(weather):
    """Clear-sky index is clipped to the configured range and only exists on sky readings."""
    readings = weather["readings"]
    csi = readings["clear_sky_index"].dropna()
    assert csi.between(*config.CSI_CLIP).all()
    assert readings.loc[~readings["is_sky_reading"], "clear_sky_index"].isna().all()


def test_every_measured_sky_reading_has_a_label(weather):
    """Every sky reading with sunlight data gets one of the 4 labels; others get none."""
    readings = weather["readings"]
    measured = readings["clear_sky_index"].notna()
    assert readings.loc[measured, "sky_label"].isin(config.SKY_LABELS).all()
    assert readings.loc[~measured, "sky_label"].isna().all()


def test_daily_label_shares_add_to_100(weather):
    """% of time in Clear + Partly cloudy + Cloudy + Overcast = 100 on every day."""
    columns = ["pct_" + label.lower().replace(" ", "_") for label in config.SKY_LABELS]
    totals = weather["daily"][columns].sum(axis=1)
    assert (totals - 100).abs().max() < 0.5
    assert weather["daily"]["sunshine_score"].between(0, 100).all()


def test_sunniest_days_look_clear(weather):
    """Sanity: midday CSI ≈ 1 on the sunniest days, and the sunniest day is labelled Clear."""
    for info in weather["metrics"]["by_plant"].values():
        assert info["sanity"]["midday_median_csi_3_sunniest_days"] > 0.9
        assert info["sunniest_day"]["dominant_sky"] == "Clear"
        assert info["cloudiest_day"]["dominant_sky"] in ["Cloudy", "Overcast", "Partly cloudy"]
        assert info["cloudiest_day"]["sunshine_score"] < info["sunniest_day"]["sunshine_score"] - 30


def test_labels_are_smoother_than_random(weather):
    """One-reading flickers are far rarer than if the same labels were shuffled randomly."""
    for info in weather["metrics"]["by_plant"].values():
        sanity = info["sanity"]
        assert sanity["single_reading_blips_pct"] < sanity["single_reading_blips_pct_if_random"] / 2


def test_day_counts_match_days(weather):
    """Clear + partly + cloudy + overcast days = number of days, per plant."""
    for info in weather["metrics"]["by_plant"].values():
        assert sum(info["days_by_dominant_sky"].values()) == info["days"] == 34


def test_sentence_for_a_made_up_day():
    """A clear morning that clouds over at 14:00 is described that way (no files needed)."""
    times = pd.date_range("2020-05-20 07:00", "2020-05-20 17:45", freq="15min")
    labels = ["Clear" if time.hour < 14 else "Cloudy" for time in times]
    day = pd.DataFrame({"timestamp": times, "hour": times.hour, "sky_label": labels})
    sentence = describe_day(day, sunshine_score=70.0, coverage_pct=100.0)
    assert sentence.startswith("Mostly clear morning, clouds after 2 PM")
    assert "30% less sunlight" in sentence
