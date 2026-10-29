"""Power vs sunlight for one inverter: the "regression against irradiance" picture.

Every daylight reading becomes a dot (x = sunlight, y = AC power). Healthy readings sit on the AI's expected
line; readings during an alert drop below it. All values come from the pipeline files — nothing is trained here.
"""

import numpy as np
import pandas as pd
from fastapi import APIRouter

from api.data_store import get_store

router = APIRouter(prefix="/api", tags=["plants"])

SUNLIGHT_BIN = 0.05            # kW/m² — width of each step of the expected line
MIN_READINGS_PER_BIN = 10      # fewer readings than this = too noisy to draw
FULL_SUN = 1.0                 # kW/m² — "full sun" reference shown in the title


def in_alert_flags(readings, alerts):
    """True for each reading that falls inside one of the inverter's alert periods (start ≤ time < end)."""
    flags = np.zeros(len(readings), dtype=bool)
    times = readings["timestamp"].to_numpy()
    for start, end in zip(alerts["start"].to_numpy(), alerts["end"].to_numpy()):
        flags |= (times >= start) & (times < end)
    return flags


def expected_line(readings):
    """The AI's expected power, as a curve against sunlight: median expected kW in each sunlight step."""
    bins = (readings["irradiation"] / SUNLIGHT_BIN).round().astype(int)
    grouped = readings.groupby(bins)["expected_kw"].agg(["median", "count"])
    grouped = grouped[grouped["count"] >= MIN_READINGS_PER_BIN]
    return [{"sunlight": round(float(b * SUNLIGHT_BIN), 3), "expected_kw": round(float(kw), 1)}
            for b, kw in grouped["median"].items()]


def healthy_r2(healthy):
    """How closely healthy readings follow the AI's expectation (1.0 = exactly on the line)."""
    if len(healthy) < 2:
        return None
    residual = ((healthy["ac_kw"] - healthy["expected_kw"]) ** 2).sum()
    spread = ((healthy["ac_kw"] - healthy["ac_kw"].mean()) ** 2).sum()
    return round(float(1 - residual / spread), 3) if spread else None


@router.get("/inverter/{inverter_id}/sunlight")
def inverter_sunlight(inverter_id: str):
    """All daylight readings of one inverter (sunlight, actual, expected, in-alert) plus the expected line."""
    store = get_store()
    plant = store.check_inverter(inverter_id)
    rows = store.expected[(store.expected["inverter"] == inverter_id) & store.expected["is_daylight"]
                          & ~store.expected["is_missing"]].dropna(subset=["irradiation", "ac_kw", "expected_kw"])
    rows = rows.sort_values("timestamp")
    alerts = store.alerts[(store.alerts["inverter"] == inverter_id) & (store.alerts["fault_type"] != "DATA_GAP")]
    flags = in_alert_flags(rows, alerts)
    line = expected_line(rows)
    near_full = [p for p in line if abs(p["sunlight"] - FULL_SUN) < SUNLIGHT_BIN / 2]
    return {
        "inverter": inverter_id, "plant": plant,
        # Short keys keep the file small: d = date, s = sunlight (kW/m²), a = actual kW, e = expected kW, f = in alert
        "points": [{"d": d, "s": round(float(s), 3), "a": round(float(a), 1), "e": round(float(e), 1), "f": bool(f)}
                   for d, s, a, e, f in zip(rows["date"], rows["irradiation"], rows["ac_kw"], rows["expected_kw"],
                                            flags)],
        "expected_line": line,
        "expected_at_full_sun_kw": near_full[0]["expected_kw"] if near_full else None,
        "healthy_r2": healthy_r2(rows[~flags]),
        "readings": int(len(rows)), "readings_in_alerts": int(flags.sum()),
    }
