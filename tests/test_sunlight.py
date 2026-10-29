"""Power vs sunlight endpoint: readings, the expected line and alert flags come straight from the pipeline files."""

from fastapi.testclient import TestClient

from api.data_store import get_store
from api.main import app
from tests.conftest import log_in


def test_sunlight_points_and_expected_line():
    """Every daylight reading is returned once; the expected line rises with sunlight; flags match alert periods."""
    store = get_store()
    inverter = store.alerts.sort_values("energy_loss_kwh").iloc[-1]["inverter"]   # an inverter with real alerts
    with TestClient(app) as client:
        log_in(client)
        sun = client.get(f"/api/inverter/{inverter}/sunlight").json()
    assert sun["readings"] == len(sun["points"]) > 0
    assert sun["readings_in_alerts"] == sum(p["f"] for p in sun["points"]) > 0
    line = [p["expected_kw"] for p in sun["expected_line"]]
    assert line[-1] > line[0]                       # more sunlight -> more expected power
    assert 0 < sun["healthy_r2"] <= 1


def test_sunlight_unknown_inverter_is_404():
    """A wrong inverter id gives a friendly 404, not a crash."""
    with TestClient(app) as client:
        log_in(client)
        assert client.get("/api/inverter/NOT_AN_INVERTER/sunlight").status_code == 404
