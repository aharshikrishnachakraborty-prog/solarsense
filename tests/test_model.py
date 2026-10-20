"""Checks that the expected-output model step produced sensible outputs (Phase 3).

Run with:   pytest
"""

import pandas as pd
import pytest

from engine import config
from engine.metrics import load_metrics


@pytest.fixture(scope="module")
def expected():
    """Load expected.parquet once for all tests in this file."""
    if not config.EXPECTED_FILE.exists():
        pytest.skip("expected.parquet not found — run: python run_all.py")
    return pd.read_parquet(config.EXPECTED_FILE)


def test_model_files_and_card_exist():
    """Both models per plant are saved, and the model card is written."""
    for plant in config.PLANTS:
        for model in ["physics", "random_forest"]:
            assert (config.MODELS_DIR / config.MODEL_FILE_TEMPLATE.format(plant=plant, model=model)).exists()
    card = config.MODEL_CARD.read_text(encoding="utf-8")
    assert "Limitations" in card and "Chosen model" in card


def test_every_daylight_row_has_a_valid_expected_value(expected):
    """Expected power is never blank or negative."""
    assert expected["expected_kw"].notna().all()
    assert (expected["expected_kw"] >= 0).all()


def test_time_split_never_mixes_days(expected):
    """Every test day comes after every training day (no peeking into the future)."""
    for _, rows in expected.groupby("plant"):
        assert rows.loc[rows["split"] == "train", "date"].max() < rows.loc[rows["split"] == "test", "date"].min()


def test_accuracy_is_good_but_not_suspicious():
    """R² on healthy test rows is high but not ≈ 1.00 (which would mean the model saw the answers)."""
    metrics = load_metrics()["expected_model"]
    for plant in config.PLANTS:
        info = metrics[f"plant_{plant}"]
        r2 = info[info["chosen_model"]]["test_without_obvious_outages"]["r2"]
        assert 0.7 < r2 < 0.995
