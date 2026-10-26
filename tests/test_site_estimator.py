"""Checks the Solar Site Planner (Phase 12). NASA is never called for real: a fake answer is used instead.

Run with:   pytest
"""

from datetime import date, datetime, timedelta

import pytest
import requests
from fastapi.testclient import TestClient

from engine import config, site_estimator
from engine.site_estimator import SiteDataUnavailable, estimate_from_daily, estimate_site, last_full_months

# A calibration that keeps the panels at exactly 25 °C when the air is 25 °C (easy to check by hand).
SIMPLE_CAL = {"plant": 1, "effective_sun_hours": 9.0, "daytime_air_offset_c": 0.0, "heating_c_per_kw_m2": 0.0,
              "heating_at_zero_sun_c": 0.0, "temp_coef_pct_per_c": -0.4}
SYSTEM = (1 - config.SITE_SYSTEM_LOSSES_PCT / 100) * config.SITE_INVERTER_EFFICIENCY_PCT / 100


class FakeNasa:
    """Stands in for requests.get: every day has 5 kWh/m² of sun and 25 °C air (except one 'missing' day)."""

    def __init__(self, fail=False):
        self.calls, self.fail = 0, fail

    def __call__(self, url, params, timeout):
        """Answer like NASA POWER does (or fail like a dead internet connection)."""
        self.calls += 1
        if self.fail:
            raise requests.ConnectionError("no internet")
        day, end = (datetime.strptime(params[key], "%Y%m%d") for key in ["start", "end"])
        sun, air = {}, {}
        while day <= end:
            key = day.strftime("%Y%m%d")
            sun[key], air[key] = (config.NASA_POWER_MISSING, 25.0) if key.endswith("0115") else (5.0, 25.0)
            day += timedelta(days=1)
        body = {"properties": {"parameter": {"ALLSKY_SFC_SW_DWN": sun, "T2M": air}}}
        return type("Response", (), {"raise_for_status": lambda self: None, "json": lambda self: body})()


@pytest.fixture
def fake_nasa(monkeypatch, tmp_path):
    """Fake NASA + an empty temporary cache folder (the real saved files are never touched)."""
    monkeypatch.setattr(config, "NASA_CACHE_DIR", tmp_path)
    fake = FakeNasa()
    monkeypatch.setattr(site_estimator.requests, "get", fake)
    return fake


def test_last_full_months_skips_months_nasa_may_not_have_yet():
    """On 26 Oct and on 5 Nov the last 12 safe months are Oct 2025 – Sep 2026 (NASA is a few days late)."""
    for today in [date(2026, 10, 26), date(2026, 11, 5)]:
        assert last_full_months(today) == (date(2025, 10, 1), date(2026, 9, 30))


def test_energy_formula_by_hand(fake_nasa):
    """Panels at 25 °C: energy = size × sunlight × system factor × days. Hotter air → less energy."""
    result = estimate_site(28.61, 77.21, 100, SIMPLE_CAL, today=date(2026, 10, 26))
    assert len(result["months"]) == config.SITE_MONTHS
    october = result["months"][0]
    assert october["expected_kwh"] == pytest.approx(100 * 5.0 * SYSTEM * 31, abs=1)
    assert result["heat_loss_pct"] == pytest.approx(0, abs=0.01)
    hot = {**SIMPLE_CAL, "daytime_air_offset_c": 10.0}    # panels 10 °C hotter → 10 × 0.4% = 4% less
    hotter = estimate_site(28.61, 77.21, 100, hot, today=date(2026, 10, 26))
    assert hotter["yearly_kwh"] == pytest.approx(result["yearly_kwh"] * 0.96, rel=0.001)


def test_missing_day_is_counted_and_filled(fake_nasa):
    """NASA's −999 'no value' is not used as sunlight; the month is filled with its average day."""
    result = estimate_site(28.61, 77.21, 100, SIMPLE_CAL, today=date(2026, 10, 26))
    january = next(m for m in result["months"] if m["month"] == "2026-01")
    assert january["days_missing"] == 1 and january["days_used"] == 30
    assert january["expected_kwh"] == pytest.approx(100 * 5.0 * SYSTEM * 31, abs=1)
    assert result["days_missing"] == 1


def test_saved_copy_avoids_a_second_download(fake_nasa):
    """The second request for the same place and year is answered from disk."""
    estimate_site(26.91, 75.79, 50, SIMPLE_CAL, today=date(2026, 10, 26))
    again = estimate_site(26.91, 75.79, 50, SIMPLE_CAL, today=date(2026, 10, 26))
    assert fake_nasa.calls == 1 and again["data_from"] == "saved copy"


def test_offline_uses_older_saved_year_or_says_so(fake_nasa):
    """No internet: an older saved year is used if there is one, else a friendly SiteDataUnavailable."""
    estimate_site(13.08, 80.27, 100, SIMPLE_CAL, today=date(2026, 10, 26))   # saves Oct 2025 – Sep 2026
    fake_nasa.fail = True
    later = estimate_site(13.08, 80.27, 100, SIMPLE_CAL, today=date(2027, 3, 1))
    assert later["data_from"].startswith("older saved copy") and later["period_end"] == "2026-09-30"
    with pytest.raises(SiteDataUnavailable, match="could not be reached"):
        estimate_site(20.0, 80.0, 100, SIMPLE_CAL, today=date(2026, 10, 26))


def test_calibration_measured_from_our_data_is_believable():
    """Measured on Plant 1: ~9 effective sunny hours a day; daytime air a few °C above the daily average."""
    if not config.WEATHER_15MIN_FILE.exists():
        pytest.skip("Run the pipeline first (python run_all.py)")
    cal = site_estimator.calibrate()
    assert 6 < cal["effective_sun_hours"] < 12
    assert 0 < cal["daytime_air_offset_c"] < 8
    assert config.BELIEVABLE_TEMP_COEF_RANGE[0] <= cal["temp_coef_pct_per_c"] <= config.BELIEVABLE_TEMP_COEF_RANGE[1]


@pytest.fixture
def client():
    """A test client that starts the app (loading all data once)."""
    if not config.METRICS_FILE.exists():
        pytest.skip("Run the pipeline first (python run_all.py)")
    from api.main import app
    with TestClient(app) as test_client:
        yield test_client


def test_api_presets_and_estimate(client, fake_nasa):
    """The page's presets, and a full estimate with 12 months and the assumptions listed."""
    presets = client.get("/api/site-estimate/presets").json()
    assert [p["name"] for p in presets["presets"]] == [p["name"] for p in config.SITE_PRESETS]
    body = client.get("/api/site-estimate", params={"lat": 28.61, "lon": 77.21, "capacity_kw": 100}).json()
    assert len(body["months"]) == config.SITE_MONTHS and body["yearly_kwh"] > 0
    assert any("ASSUMPTION" in a["source"] for a in body["assumptions"])
    assert "kWh a year" in body["takeaway"]


def test_api_rejects_places_outside_india_and_reports_nasa_down(client, fake_nasa):
    """London → 422 (bad input). NASA unreachable with nothing saved → 503 with a friendly message."""
    assert client.get("/api/site-estimate", params={"lat": 51.5, "lon": -0.1, "capacity_kw": 100}).status_code == 422
    assert client.get("/api/site-estimate", params={"lat": 20, "lon": 80, "capacity_kw": 0}).status_code == 422
    fake_nasa.fail = True
    response = client.get("/api/site-estimate", params={"lat": 20, "lon": 80, "capacity_kw": 100})
    assert response.status_code == 503 and "could not be reached" in response.json()["detail"]
