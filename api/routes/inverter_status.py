"""Status of every inverter of a plant on one day — colours the 3D plant view on the Overview page.

The status comes only from that day's alerts (no new calculation, no ML):
  critical = an inverter trip, or any Critical alert        (red)
  warning  = any other alert, e.g. underperformance          (amber)
  offline  = only data-gap alerts: we could not see it       (grey)
  normal   = no alerts that day                              (green)
"""

from typing import Optional

import pandas as pd
from fastapi import APIRouter

from api.data_store import get_store

router = APIRouter(prefix="/api", tags=["plants"])

STATUSES = ["normal", "warning", "critical", "offline"]
OPEN_STATUSES = ["Open", "Acknowledged"]   # same meaning as "Active" on the Alerts page


def status_of(alerts):
    """One inverter's status from its alerts on the day (most serious wins)."""
    if alerts.empty:
        return "normal"
    is_gap = alerts["fault_type"] == "DATA_GAP"
    if ((alerts["fault_type"] == "INVERTER_TRIP") | ((alerts["severity"] == "Critical") & ~is_gap)).any():
        return "critical"
    if (~is_gap).any():
        return "warning"
    return "offline"


def number(value, digits=1):
    """A rounded float, or None when the value is missing."""
    return None if value is None or pd.isna(value) else round(float(value), digits)


@router.get("/inverters/status")
def inverters_status(plant: int = 1, date: Optional[str] = None):
    """Every inverter of the plant on one day: status, actual vs expected energy, losses and open alerts."""
    store = get_store()
    plant = store.check_plant(plant)
    date = store.check_date(date, plant)
    day = store.daily_inverter[(store.daily_inverter["plant"] == plant) & (store.daily_inverter["date"] == date)]
    day = day.set_index("inverter")
    alerts = store.alerts_on_date(plant, date)
    alerts = alerts[alerts["inverter"] != "ALL"]   # plant-wide notices belong to no single inverter

    inverters = sorted(store.daily_inverter.loc[store.daily_inverter["plant"] == plant, "inverter"].unique())
    rows = []
    for inverter in inverters:
        own = alerts[alerts["inverter"] == inverter]
        energy = day.loc[inverter] if inverter in day.index else None
        biggest = own.assign(size=own["energy_loss_kwh"] + own["energy_at_risk_kwh"]).nlargest(1, "size")
        rows.append({
            "inverter": inverter,
            "status": status_of(own),
            "actual_kwh": None if energy is None else number(energy["actual_kwh"]),
            "expected_kwh": None if energy is None else number(energy["expected_kwh"]),
            "ratio": None if energy is None else number(energy["performance_ratio"], 4),
            "loss_kwh": 0.0 if energy is None else number(energy["fault_loss_kwh"]) or 0.0,
            "loss_inr": 0.0 if energy is None else number(energy["fault_loss_inr"], 0) or 0.0,
            "at_risk_kwh": 0.0 if energy is None else number(energy["at_risk_kwh"]) or 0.0,
            "open_alerts": int(own["status"].isin(OPEN_STATUSES).sum()),
            "main_fault": None if biggest.empty else biggest["fault_type"].iloc[0],
        })
    counts = {status: sum(r["status"] == status for r in rows) for status in STATUSES}
    return {"plant": plant, "date": date, "inverters": rows, "counts": counts}
