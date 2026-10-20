"""Endpoints about plants and inverters: list, overview KPIs, time series, heatmap, inverter detail."""

from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter

from api.data_store import get_store, to_records
from api.routes.alerts import ALERT_FIELDS
from api.schemas import HeatmapResponse, InverterResponse, Overview, PlantsResponse, TimeseriesResponse
from engine import config

router = APIRouter(prefix="/api", tags=["plants"])


@router.get("/plants", response_model=PlantsResponse)
def plants():
    """List plants with inverter counts, the dates available for replay, and each plant's
    highest-loss day (the default replay date, so the demo opens on the most interesting day)."""
    store = get_store()
    info = []
    for plant in store.plants:
        days = store.daily_inverter[store.daily_inverter["plant"] == plant]
        info.append({"plant": plant, "inverters": int(days["inverter"].nunique()),
                     "first_date": days["date"].min(), "last_date": days["date"].max(),
                     "worst_loss_date": store.worst_loss_date(plant)})
    return {"plants": info, "dates": store.dates, "default_plant": store.plants[0],
            "default_date": info[0]["worst_loss_date"]}


def _indian(value):
    """Whole number with Indian digit grouping, rounding .5 up — same as the website (e.g. 1,53,809)."""
    digits = str(int(np.floor(value + 0.5)))
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = [head[max(i - 2, 0):i] for i in range(len(head), 0, -2)][::-1]
    return ",".join(groups + [tail])


def _takeaway(plant, date, needing_attention, day):
    """One plain-English sentence summarising the plant's day (all numbers from the data)."""
    pretty = pd.Timestamp(date).strftime("%d %b %Y")
    if needing_attention == 0 and day["fault_loss_kwh"] == 0:
        return (f"Plant {plant} on {pretty}: all inverters performing as expected "
                f"(actual vs expected {_indian(100 * day['performance_ratio'])}%).")
    noun = "inverter needs" if needing_attention == 1 else "inverters need"
    return (f"Plant {plant} on {pretty}: {needing_attention} {noun} attention — estimated loss "
            f"{_indian(day['fault_loss_kwh'])} kWh (₹{_indian(day['fault_loss_inr'])}) that day.")


@router.get("/overview", response_model=Overview)
def overview(plant: int = 1, date: Optional[str] = None):
    """KPI cards for one plant and day, plus a one-line takeaway."""
    store = get_store()
    plant = store.check_plant(plant)
    date = store.check_date(date, plant)
    day = store.daily_plant[(store.daily_plant["plant"] == plant) & (store.daily_plant["date"] == date)].iloc[0]
    active = store.alerts_on_date(plant, date)
    active = active[active["status"] != "Resolved"]
    # Plant-wide data-quality notices (no energy lost) are shown separately, not as alerts to act on.
    notices = active[store.is_notice(active)]
    active = active[~store.is_notice(active)]
    by_severity = {level: int((active["severity"] == level).sum()) for level in config.SEVERITY_LEVELS}
    needing_attention = int(active.loc[active["inverter"] != "ALL", "inverter"].nunique())
    losses = store.metrics["losses"]
    return {"plant": plant, "date": date, "takeaway": _takeaway(plant, date, needing_attention, day),
            "data_quality_notices": to_records(notices[["id", "severity", "reason"]]),
            "actual_kwh": day["actual_kwh"], "expected_kwh": day["expected_kwh"],
            "performance_ratio": None if pd.isna(day["performance_ratio"]) else day["performance_ratio"],
            "fault_loss_kwh": day["fault_loss_kwh"], "fault_loss_inr": day["fault_loss_inr"],
            "at_risk_kwh": day["at_risk_kwh"], "at_risk_inr": day["at_risk_inr"],
            "active_alerts_by_severity": by_severity, "inverters_needing_attention": needing_attention,
            "tariff_inr_per_kwh": losses["tariff_inr_per_kwh"], "tariff_note": losses["tariff_note"]}


@router.get("/plant/timeseries", response_model=TimeseriesResponse)
def plant_timeseries(plant: int = 1, date: Optional[str] = None):
    """15-minute plant total: actual vs expected (on readings we have) and sunlight, for one day."""
    store = get_store()
    plant = store.check_plant(plant)
    date = store.check_date(date, plant)
    rows = store.expected[(store.expected["plant"] == plant) & (store.expected["date"] == date)]
    present = rows[~rows["is_missing"]]
    points = pd.DataFrame({
        "actual_kw": present.groupby("timestamp")["ac_kw"].sum(),
        "expected_kw": present.groupby("timestamp")["expected_kw"].sum(),
        "expected_kw_all": rows.groupby("timestamp")["expected_kw"].sum(),
        "irradiation": rows.groupby("timestamp")["irradiation"].first(),
        "missing_inverters": rows.groupby("timestamp")["is_missing"].sum(),
    }).fillna({"actual_kw": 0, "expected_kw": 0}).round(2).reset_index()
    return {"plant": plant, "date": date, "points": to_records(points)}


@router.get("/plant/daily")
def plant_daily(plant: int = 1):
    """Daily actual vs expected energy (and their ratio) and loss for one plant (all days)."""
    store = get_store()
    plant = store.check_plant(plant)
    days = store.daily_plant[store.daily_plant["plant"] == plant].sort_values("date")
    columns = ["date", "actual_kwh", "expected_kwh", "performance_ratio", "fault_loss_kwh",
               "fault_loss_inr", "at_risk_kwh"]
    total_actual, total_expected = days["actual_kwh"].sum(), days["expected_kwh"].sum()
    return {"plant": plant, "days": to_records(days[columns]),
            "period_performance_ratio": round(float(total_actual / total_expected), 4)}


@router.get("/plant/heatmap", response_model=HeatmapResponse)
def plant_heatmap(plant: int = 1):
    """Daily actual vs expected ratio per inverter (rows = inverters, columns = days)."""
    store = get_store()
    plant = store.check_plant(plant)
    days = store.daily_inverter[store.daily_inverter["plant"] == plant]
    pr = days.pivot(index="inverter", columns="date", values="performance_ratio")
    loss = days.pivot(index="inverter", columns="date", values="fault_loss_kwh").fillna(0)
    pr = pr.astype(object).where(pr.notna(), None)
    return {"plant": plant, "inverters": list(pr.index), "dates": list(pr.columns),
            "performance_ratio": pr.values.tolist(), "fault_loss_kwh": loss.values.tolist()}


@router.get("/inverter/{inverter_id}", response_model=InverterResponse)
def inverter_detail(inverter_id: str, date: Optional[str] = None):
    """One inverter: 15-min actual vs expected vs peer median, its alerts, and daily PR history."""
    store = get_store()
    plant, date = store.check_inverter(inverter_id), store.check_date(date)
    rows = store.expected[(store.expected["inverter"] == inverter_id) & (store.expected["date"] == date)]
    series = rows[["timestamp", "ac_kw", "expected_kw", "peer_median_kw", "is_missing", "irradiation"]]
    series = series.rename(columns={"ac_kw": "actual_kw"}).sort_values("timestamp")

    alerts = store.alerts_with_status()
    own = alerts[alerts["inverter"] == inverter_id].sort_values("start")[ALERT_FIELDS]

    history = store.daily_inverter[store.daily_inverter["inverter"] == inverter_id][
        ["date", "actual_kwh", "expected_kwh", "performance_ratio", "fault_loss_kwh", "fault_loss_inr", "at_risk_kwh"]]
    hints = store.anomaly[store.anomaly["inverter"] == inverter_id][["date", "anomaly_score", "is_unusual"]]
    history = history.merge(hints, on="date", how="left").sort_values("date")
    return {"inverter": inverter_id, "plant": plant, "date": date, "series": to_records(series),
            "alerts": to_records(own), "daily_history": to_records(history), "pr_trend": _pr_trend(history)}


def _pr_trend(history):
    """Straight-line fit through the daily actual vs expected ratio (a display aid, not a detector)."""
    usable = history.dropna(subset=["performance_ratio"])
    if len(usable) < 2:
        return None
    day_number = (pd.to_datetime(usable["date"]) - pd.to_datetime(usable["date"].iloc[0])).dt.days
    slope, intercept = np.polyfit(day_number, usable["performance_ratio"], 1)
    return {"slope_pct_per_day": round(float(100 * slope), 3),
            "points": [{"date": d, "performance_ratio": round(float(intercept + slope * n), 4)}
                       for d, n in zip(usable["date"], day_number)]}
