"""Checks every API endpoint with FastAPI's TestClient (Phase 8).

Run with:   pytest
The status-update test writes to a TEMPORARY file, never the real alert_status.json.
"""

import pytest
from fastapi.testclient import TestClient

from engine import config


@pytest.fixture(scope="module")
def client():
    """A test client that starts the app (loading all data once)."""
    if not config.ALERTS_FILE.exists():
        pytest.skip("Run the pipeline first (python run_all.py)")
    from api.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def temp_status_file(tmp_path, monkeypatch):
    """Point the status file at a temporary location for this test only."""
    monkeypatch.setattr(config, "ALERT_STATUS_FILE", tmp_path / "alert_status.json")


def test_health(client):
    """The server answers the health check."""
    assert client.get("/api/health").json() == {"status": "ok"}


def test_plants(client):
    """Both plants are listed and the default date is a real date."""
    body = client.get("/api/plants").json()
    assert [p["plant"] for p in body["plants"]] == [1, 2]
    assert body["default_date"] in body["dates"]


def _worst_loss_date(plant):
    """Highest fault-loss day of a plant, read straight from the daily table."""
    import pandas as pd
    days = pd.read_parquet(config.DAILY_PLANT_FILE).query("plant == @plant")
    return days.loc[days["fault_loss_kwh"].idxmax(), "date"]


def test_overview_defaults_and_takeaway(client):
    """With no inputs, the overview shows Plant 1 on its highest-loss day, in plain words."""
    body = client.get("/api/overview").json()
    assert body["plant"] == 1 and body["date"] == _worst_loss_date(1)
    assert body["takeaway"].startswith("Plant 1")
    assert "performance ratio" not in body["takeaway"].lower()
    assert set(body["active_alerts_by_severity"]) == set(config.SEVERITY_LEVELS)


def test_default_replay_date_is_highest_loss_day(client):
    """Each plant's default replay date is its highest-loss day."""
    body = client.get("/api/plants").json()
    for info in body["plants"]:
        assert info["worst_loss_date"] == _worst_loss_date(info["plant"])
    assert body["default_date"] == body["plants"][0]["worst_loss_date"]


def test_data_quality_notices_are_not_counted_as_alerts(client):
    """Sensor issues with no loss are notices, not alerts to act on."""
    body = client.get("/api/overview", params={"plant": 1, "date": "2020-06-17"}).json()
    assert body["data_quality_notices"], "Plant 1 has plant-wide sensor issues"
    assert sum(body["active_alerts_by_severity"].values()) == 0   # only notices that day
    listed = client.get("/api/alerts", params={"plant": 1, "include_notices": "false"}).json()["alerts"]
    assert not [a for a in listed if a["fault_type"] == "SENSOR_ISSUE" and a["energy_loss_kwh"] == 0]
    assert client.get("/api/alerts", params={"plant": 1}).json()["count"] > len(listed)   # still on Alerts page


def test_overview_numbers_match_daily_table(client):
    """Overview loss equals the number in the daily table."""
    import pandas as pd
    day = pd.read_parquet(config.DAILY_PLANT_FILE).query("plant == 2 and date == '2020-06-08'").iloc[0]
    body = client.get("/api/overview", params={"plant": 2, "date": "2020-06-08"}).json()
    assert body["fault_loss_kwh"] == pytest.approx(day["fault_loss_kwh"])


def test_timeseries(client):
    """The day chart gets a full day of 15-minute points."""
    body = client.get("/api/plant/timeseries", params={"plant": 2, "date": "2020-06-08"}).json()
    assert len(body["points"]) > 40
    assert {"actual_kw", "expected_kw", "irradiation"} <= set(body["points"][0])


def test_heatmap_shape(client):
    """The heatmap has one row per inverter and one column per day."""
    body = client.get("/api/plant/heatmap", params={"plant": 1}).json()
    assert len(body["performance_ratio"]) == len(body["inverters"]) == 22
    assert all(len(row) == len(body["dates"]) for row in body["performance_ratio"])


def test_inverter_detail(client):
    """Inverter detail returns its series, alerts, history and trend line."""
    body = client.get("/api/inverter/LYwnQax7tkwH5Cb", params={"date": "2020-06-08"}).json()
    assert body["plant"] == 2 and body["series"] and body["alerts"] and len(body["daily_history"]) == 34
    assert len(body["pr_trend"]["points"]) > 1


def test_plant_daily(client):
    """Daily plant losses add up to the plant's total loss."""
    body = client.get("/api/plant/daily", params={"plant": 2}).json()
    assert len(body["days"]) == 34
    losses = client.get("/api/losses", params={"plant": 2}).json()["total"]["fault_loss_kwh"]
    assert sum(d["fault_loss_kwh"] for d in body["days"]) == pytest.approx(losses, abs=1)


def test_alert_filters_and_sorting(client):
    """Alert filters work and sort=loss puts the biggest loss first."""
    body = client.get("/api/alerts", params={"plant": 2, "type": "INVERTER_TRIP", "sort": "loss"}).json()
    losses = [a["energy_loss_kwh"] for a in body["alerts"]]
    assert body["count"] > 0 and losses == sorted(losses, reverse=True)
    assert all(a["plant"] == 2 and a["fault_type"] == "INVERTER_TRIP" for a in body["alerts"])


def test_alert_date_filter(client):
    """date= keeps only alerts that happened on that day."""
    body = client.get("/api/alerts", params={"plant": 2, "date": "2020-06-08"}).json()
    assert body["count"] > 0
    assert all(a["start"] < "2020-06-09" and a["end"] > "2020-06-08" for a in body["alerts"])


def test_alert_detail_has_evidence_series(client):
    """An alert detail includes the evidence used by the 'Why?' chart."""
    body = client.get("/api/alerts/P1-TRIP-0001").json()
    assert body["series_kind"] == "intervals" and any(point["in_alert"] for point in body["series"])
    assert body["reason"] and body["evidence"]


def test_status_update_round_trip(client, temp_status_file):
    """Acknowledging an alert is saved and read back."""
    response = client.post("/api/alerts/P1-TRIP-0001/status", json={"status": "Acknowledged"})
    assert response.status_code == 200 and response.json()["status"] == "Acknowledged"
    assert client.get("/api/alerts/P1-TRIP-0001").json()["status"] == "Acknowledged"


def test_invalid_status_is_rejected(client, temp_status_file):
    """Unknown statuses are refused."""
    assert client.post("/api/alerts/P1-TRIP-0001/status", json={"status": "Deleted"}).status_code == 422


def test_losses_match_metrics(client):
    """Plant losses add up to the overall total."""
    total = client.get("/api/losses").json()["total"]["fault_loss_kwh"]
    by_plant = sum(client.get("/api/losses", params={"plant": p}).json()["total"]["fault_loss_kwh"] for p in [1, 2])
    assert by_plant == pytest.approx(total, abs=1)


def test_validation_and_assumptions(client):
    """Validation results and the assumptions list are served."""
    assert "by_fault" in client.get("/api/validation").json()
    keys = [a["key"] for a in client.get("/api/assumptions").json()]
    assert "tariff_inr_per_kwh" in keys


@pytest.mark.parametrize("url", ["/api/alerts/NOPE", "/api/overview?date=2021-01-01",
                                 "/api/overview?plant=9", "/api/inverter/XYZ"])
def test_friendly_404s(client, url):
    """Bad inputs get a friendly 'not found' message."""
    response = client.get(url)
    assert response.status_code == 404 and "not found" in response.json()["detail"].lower() \
        or "no data" in response.json()["detail"].lower()


def test_replay_ends_at_the_days_totals(client):
    """The last replay tick must equal the day's numbers from the daily table."""
    import pandas as pd
    day = pd.read_parquet(config.DAILY_PLANT_FILE).query("plant == 2 and date == '2020-06-08'").iloc[0]
    body = client.get("/api/replay", params={"plant": 2, "date": "2020-06-08"}).json()
    last = body["ticks"][-1]
    assert last["actual_kwh"] == pytest.approx(day["actual_kwh"], abs=1)
    assert last["fault_loss_kwh"] == pytest.approx(day["fault_loss_kwh"], abs=1)
    assert [t["actual_kwh"] for t in body["ticks"]] == sorted(t["actual_kwh"] for t in body["ticks"])
    assert body["events"] and all(0 <= e["tick"] < len(body["ticks"]) for e in body["events"])


def test_figures_are_served(client):
    """Pipeline charts (PNG) are available to the website."""
    assert client.get("/figures/validation_injected_fault_caught.png").status_code == 200


def test_takeaway_numbers_match_the_website_format():
    """Takeaway uses Indian grouping and rounds .5 up, like the website tiles (e.g. 1,53,809)."""
    from api.routes.plants import _indian
    assert [_indian(v) for v in [999, 8852.5, 153808.5, 2783041]] == ["999", "8,853", "1,53,809", "27,83,041"]


def test_settings_match_config(client):
    """The website reads thresholds from the API, so they must equal engine/config.py."""
    body = client.get("/api/settings").json()
    assert body["underperformance_drop_pct"] == -config.UNDER_RESIDUAL_PCT_MAX
    assert body["tariff_inr_per_kwh"] == config.TARIFF_INR_PER_KWH


def test_static_file_names_match_the_website():
    """The static export must name files exactly like staticFile() in web/js/api.js."""
    from api.export_static import static_name
    assert static_name({}) == "index"
    assert static_name({"plant": "2", "date": "2020-05-27"}) == "date-2020-05-27__plant-2"
