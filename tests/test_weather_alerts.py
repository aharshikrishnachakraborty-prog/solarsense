"""Checks the weather-aware alerts: sky, confidence, weather sentence and the before/after test (Phase W4).

Run with:   pytest
"""

import pandas as pd
import pytest

from engine import config
from engine.alert_text import make_confidence, make_weather_note
from engine.alert_weather import needs_more_proof
from engine.metrics import load_metrics

CLEAR_UNDER = {"sky_condition": "Clear", "avg_csi": 0.95, "difficult_sky_share": 0.0, "avg_module_temp_c": 55.0,
               "avg_peer_ratio": 0.7, "intervals": 4}


@pytest.fixture(scope="module")
def alerts():
    """The alerts table (skip if the pipeline has not run)."""
    if not config.ALERTS_FILE.exists():
        pytest.skip("alerts.parquet not found — run: python -m engine.detect_faults")
    return pd.read_parquet(config.ALERTS_FILE)


def test_every_alert_has_confidence_and_weather_sentence(alerts):
    """Each alert has High/Medium/Low confidence and a non-empty weather sentence."""
    assert alerts["confidence"].isin(config.CONFIDENCE_LEVELS).all()
    assert alerts["weather_note"].str.len().gt(20).all()


def test_sky_is_a_known_label(alerts):
    """Sky during an alert is one of the 4 labels, or blank for whole-period / multi-day alerts."""
    known = alerts["sky_condition"].dropna()
    assert known.isin(config.SKY_LABELS).all()
    timed = alerts["fault_type"].isin(["INVERTER_TRIP", "UNDERPERFORMANCE"])
    assert alerts.loc[timed, "sky_condition"].notna().mean() > 0.95   # nearly all have a weather reading


def test_clear_sky_sentence_says_not_clouds():
    """Clear sky + low output → the sentence says clouds are NOT the cause, confidence High."""
    assert "NOT caused by clouds" in make_weather_note("UNDERPERFORMANCE", CLEAR_UNDER)
    assert make_confidence("UNDERPERFORMANCE", CLEAR_UNDER) == "High"


def test_difficult_sky_lowers_confidence_and_strong_peer_gap_raises_it():
    """Overcast/changing sky → Low; far below neighbours → one level up."""
    cloudy = {**CLEAR_UNDER, "sky_condition": "Overcast", "avg_csi": 0.2, "difficult_sky_share": 1.0}
    assert make_confidence("UNDERPERFORMANCE", cloudy) == "Low"
    assert make_confidence("UNDERPERFORMANCE", {**cloudy, "avg_peer_ratio": 0.3}) == "Medium"
    assert make_confidence("INVERTER_TRIP", cloudy) == "Medium"
    assert make_confidence("DATA_GAP", cloudy) == "High"


def test_weather_rule_only_drops_short_weak_events_under_difficult_sky(monkeypatch):
    """With the rule ON: short + difficult sky + weak peer gap → dropped; long or strong peer gap → kept."""
    monkeypatch.setattr(config, "WEATHER_AWARE_UNDER", True)
    shaky = {**CLEAR_UNDER, "difficult_sky_share": 0.8}
    assert needs_more_proof("UNDERPERFORMANCE", shaky)
    assert not needs_more_proof("UNDERPERFORMANCE", {**shaky, "intervals": config.UNDER_DIFFICULT_MIN_INTERVALS})
    assert not needs_more_proof("UNDERPERFORMANCE", {**shaky, "avg_peer_ratio": 0.3})
    assert not needs_more_proof("UNDERPERFORMANCE", CLEAR_UNDER)
    assert not needs_more_proof("INVERTER_TRIP", shaky)
    monkeypatch.setattr(config, "WEATHER_AWARE_UNDER", False)
    assert not needs_more_proof("UNDERPERFORMANCE", shaky)


def test_before_after_validation_exists_and_config_follows_it():
    """Both versions were tested at both settings, and the rule is only ON if the test said keep it."""
    result = load_metrics().get("validation_weather")
    if result is None:
        pytest.skip("no validation_weather — run: python -m engine.validate_weather")
    pairs = {(r["setting"], r["version"]) for r in result["results"]}
    assert pairs == {(s, v) for s in ["default", "sensitive"] for v in ["before", "after"]}
    if config.WEATHER_AWARE_UNDER:
        assert result["keep_rule"], "The weather rule is ON although the before/after test said not to keep it"
    assert result["rule_enabled_in_config"] == config.WEATHER_AWARE_UNDER
