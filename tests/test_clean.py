"""Checks that data/processed/clean.parquet is built correctly (Phase 2).

Run with:   pytest
"""

import pandas as pd
import pytest

from engine import config
from engine.load_data import load_generation


@pytest.fixture(scope="module")
def clean():
    """Load the clean table once for all tests in this file."""
    if not config.CLEAN_FILE.exists():
        pytest.skip("clean.parquet not found — run: python -m engine.clean_data")
    return pd.read_parquet(config.CLEAN_FILE)


def test_no_duplicate_inverter_timestamps(clean):
    """Each inverter must have at most one row per timestamp."""
    assert not clean.duplicated(["plant", "inverter", "timestamp"]).any()


def test_timestamps_every_15_minutes(clean):
    """Within each inverter, consecutive rows must be exactly 15 minutes apart."""
    gaps = clean.sort_values("timestamp").groupby(["plant", "inverter"])["timestamp"].diff().dropna()
    assert (gaps == pd.Timedelta(minutes=15)).all()


def test_every_inverter_has_full_grid(clean):
    """Every inverter gets every slot: days × 96 rows."""
    rows_per_inverter = clean.groupby(["plant", "inverter"]).size()
    days = clean["date"].nunique()
    assert (rows_per_inverter == days * config.READINGS_PER_DAY).all()


def test_is_missing_matches_raw_data(clean):
    """Non-missing rows must be exactly the readings that exist in the raw files."""
    for plant in config.PLANTS:
        raw_rows = len(load_generation(plant))
        present = (~clean.loc[clean["plant"] == plant, "is_missing"]).sum()
        assert present == raw_rows


def test_missing_rows_have_no_invented_power(clean):
    """Missing readings must have blank power, and real readings must have a value."""
    missing = clean[clean["is_missing"]]
    present = clean[~clean["is_missing"]]
    assert missing["ac_kw"].isna().all() and missing["dc_kw"].isna().all()
    assert present["ac_kw"].notna().all()


def test_no_negative_power(clean):
    """Power can never be negative."""
    assert (clean["ac_kw"].dropna() >= 0).all()
    assert (clean["dc_kw"].dropna() >= 0).all()


def test_dc_fix_gives_realistic_ratio(clean):
    """After the fix, both plants should keep roughly 90–100% of DC as AC in daylight."""
    daylight = clean[clean["is_daylight"] & (clean["dc_kw"] > 0)]
    ratio = (daylight["ac_kw"] / daylight["dc_kw"]).groupby(daylight["plant"]).median()
    assert ratio.between(0.9, 1.0).all()
