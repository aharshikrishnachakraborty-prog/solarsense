"""Inverter status endpoint (colours of the Overview 3D view): one row per inverter, and the red blocks
are exactly the inverters with a trip or a Critical alert on the Alerts page for that day."""

from fastapi.testclient import TestClient

from api.data_store import get_store
from api.main import app
from api.routes.inverter_status import STATUSES
from tests.conftest import log_in


def test_every_inverter_gets_one_status():
    """Each plant: one row per inverter, a known status for each, and counts that add up."""
    store = get_store()
    with TestClient(app) as client:
        log_in(client)
        for plant in store.plants:
            body = client.get("/api/inverters/status", params={"plant": plant}).json()
            inverters = store.daily_inverter.loc[store.daily_inverter["plant"] == plant, "inverter"].unique()
            assert len(body["inverters"]) == len(inverters)
            assert all(row["status"] in STATUSES for row in body["inverters"])
            assert sum(body["counts"].values()) == len(inverters)
            for status in STATUSES:
                assert body["counts"][status] == sum(row["status"] == status for row in body["inverters"])


def test_red_blocks_match_the_alerts_page():
    """On the default (biggest-loss) day, critical = inverters with a trip or Critical alert in /api/alerts."""
    store = get_store()
    with TestClient(app) as client:
        log_in(client)
        for plant in store.plants:
            body = client.get("/api/inverters/status", params={"plant": plant}).json()
            alerts = client.get("/api/alerts", params={"plant": plant, "date": body["date"]}).json()["alerts"]
            serious = {a["inverter"] for a in alerts if a["inverter"] != "ALL" and a["fault_type"] != "DATA_GAP"
                       and (a["fault_type"] == "INVERTER_TRIP" or a["severity"] == "Critical")}
            red = {row["inverter"] for row in body["inverters"] if row["status"] == "critical"}
            assert red == serious
            assert red, "the biggest-loss day should have at least one red block"


def test_bad_plant_or_date_is_404():
    """Wrong plant or a day outside the data gives a friendly 404, not a crash."""
    with TestClient(app) as client:
        log_in(client)
        assert client.get("/api/inverters/status", params={"plant": 9}).status_code == 404
        assert client.get("/api/inverters/status", params={"plant": 1, "date": "2019-01-01"}).status_code == 404
