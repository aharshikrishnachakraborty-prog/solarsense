"""Endpoints for the Weather & Energy page: one day's sky and heat, the weather calendar, the temperature
effect and the energy waterfall (Phases W1–W3). They only read files the pipeline already made."""

from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException

from api.data_store import get_store, to_records
from api.routes.plants import _indian
from api.schemas import BreakdownResponse, WeatherCalendarResponse, WeatherDayResponse, WeatherTemperatureResponse
from engine import config

router = APIRouter(prefix="/api", tags=["weather"])

DAY_COLUMNS = ["timestamp", "irradiation", "clear_sky_irr", "clear_sky_index", "sky_label", "ambient_temp",
               "module_temp", "is_hot_hour", "plant_actual_kw", "plant_expected_kw", "power_at_25c_kw", "heat_loss_kw"]
CALENDAR_COLUMNS = ["date", "dominant_sky", "sunshine_score", "max_module_c", "summary", "temperature_summary"]
WATERFALL_PARTS = ["cloud_loss_kwh", "heat_loss_kwh", "fault_loss_kwh", "not_measured_kwh", "other_kwh"]


def _weather_store():
    """The data store, or a friendly 404 if the weather steps (W1–W3) have not been run yet."""
    store = get_store()
    if not store.weather_ready:
        raise HTTPException(404, "Weather results not found — run the pipeline (python run_all.py).")
    return store


def _one_day(table, plant, date):
    """The single row of a daily table for this plant and date."""
    rows = table[(table["plant"] == plant) & (table["date"] == date)]
    return rows.iloc[0] if len(rows) else None


def _waterfall(row_or_totals):
    """Waterfall steps in order (potential → each loss → actual), with each loss's kind (natural/fixable/unknown)."""
    steps = [{"part": "clear_sky_potential", "kwh": float(row_or_totals["clear_sky_potential_kwh"]), "kind": "potential"}]
    for part in WATERFALL_PARTS:
        steps.append({"part": part.replace("_kwh", ""), "kwh": float(row_or_totals[part]),
                      "kind": config.BREAKDOWN_PARTS[part]})
    steps.append({"part": "actual", "kwh": float(row_or_totals["actual_kwh"]), "kind": "actual"})
    potential = steps[0]["kwh"]
    return [{**step, "kwh": round(step["kwh"], 1),
             "pct_of_potential": round(100 * step["kwh"] / potential, 2) if potential else None} for step in steps]


def _loss_totals(steps):
    """Natural (clouds + heat) and fixable (faults) energy of a waterfall, in kWh."""
    return {"natural_loss_kwh": round(sum(s["kwh"] for s in steps if s["kind"] == "natural"), 1),
            "fixable_loss_kwh": round(sum(s["kwh"] for s in steps if s["kind"] == "fixable"), 1)}


@router.get("/weather/day", response_model=WeatherDayResponse)
def weather_day(plant: int = 1, date: Optional[str] = None):
    """15-minute sunlight vs clear-sky curve, sky label, air & panel temperature, actual & expected power and
    heat loss for one day — plus the day's sky and temperature sentences and its waterfall."""
    store = _weather_store()
    plant = store.check_plant(plant)
    date = store.check_date(date, plant)
    rows = store.weather_15min[(store.weather_15min["plant"] == plant) & (store.weather_15min["date"] == date)]
    # Only the hours a clear sky gives real sunlight (tiny night-time sensor noise is left out).
    rows = rows[rows["clear_sky_irr"] > config.DAYLIGHT_IRRADIATION_THRESHOLD].sort_values("timestamp")
    sky = _one_day(store.weather_daily, plant, date)
    waterfall = _one_day(store.breakdown, plant, date)
    day = {key: sky[key] for key in ["dominant_sky", "sunshine_score", "avg_csi", "coverage_pct", "summary",
                                     "min_ambient_c", "max_ambient_c", "max_module_c", "hot_hours", "heat_loss_kwh",
                                     "heat_loss_inr", "heat_loss_pct", "temperature_summary"]}
    day["max_module_time"] = sky["max_module_time"].strftime("%Y-%m-%dT%H:%M:%S")
    day["fault_loss_inr"] = float(waterfall["fault_loss_inr"])
    steps = _waterfall(waterfall)
    shares = {label: float(sky["pct_" + label.lower().replace(" ", "_")]) for label in config.SKY_LABELS}
    pretty = pd.Timestamp(date).strftime("%d %b")
    sky_words = sky["summary"].rstrip(".").split(" — ")[0]
    takeaway = (f"{pretty}: {sky_words[0].lower() + sky_words[1:]} — clouds cost "
                f"{_indian(waterfall['cloud_loss_kwh'])} kWh, heat cost {_indian(waterfall['heat_loss_kwh'])} kWh, "
                f"faults cost {_indian(waterfall['fault_loss_kwh'])} kWh.")
    return {"plant": plant, "date": date, "takeaway": takeaway, "day": to_records(pd.DataFrame([day]))[0],
            "sky_share_pct": shares, "points": to_records(rows[DAY_COLUMNS]),
            "waterfall": steps, **_loss_totals(steps), "hot_module_temp_c": config.HOT_MODULE_TEMP_C,
            "note": store.metrics["weather"]["method"]["note"]}


@router.get("/weather/calendar", response_model=WeatherCalendarResponse)
def weather_calendar(plant: int = 1):
    """Every day of one plant: dominant sky, sunshine score, max panel temperature, actual energy and its waterfall."""
    store = _weather_store()
    plant = store.check_plant(plant)
    days = store.weather_daily[store.weather_daily["plant"] == plant][CALENDAR_COLUMNS]
    parts = store.breakdown[store.breakdown["plant"] == plant][
        ["date", "clear_sky_potential_kwh", *WATERFALL_PARTS, "actual_kwh"]]
    days = days.merge(parts, on="date").sort_values("date")
    counts = days["dominant_sky"].value_counts().reindex(config.SKY_LABELS, fill_value=0)
    return {"plant": plant, "days": to_records(days), "days_by_sky": {k: int(v) for k, v in counts.items()},
            "sky_labels": config.SKY_LABELS}


@router.get("/weather/temperature", response_model=WeatherTemperatureResponse)
def weather_temperature(plant: int = 1):
    """Panel temperature vs efficiency: sampled healthy readings, averages per 2 °C, the fitted line and the
    measured temperature coefficient with its honest verdict."""
    store = _weather_store()
    plant = store.check_plant(plant)
    info = store.metrics["temperature"]["by_plant"][f"plant_{plant}"]
    points = store.temperature_points[store.temperature_points["plant"] == plant][["module_temp", "efficiency_pct"]]
    keep = ["coefficient_pct_per_c", "ci95_pct_per_c", "rows", "days", "fit_line", "binned", "verdict",
            "by_sunlight_band_pct_per_c", "coefficient_used_pct_per_c", "coefficient_source", "panel_heating",
            "heat_loss_kwh_total", "heat_loss_inr_total", "heat_loss_pct_of_25c_energy", "hot_hours_total"]
    return {"plant": plant, **{key: info[key] for key in keep}, "points": to_records(points),
            "typical_range_pct_per_c": store.metrics["temperature"]["typical_range_pct_per_c"],
            "reference_panel_temp_c": config.REFERENCE_PANEL_TEMP_C}


@router.get("/breakdown", response_model=BreakdownResponse)
def breakdown(plant: Optional[int] = None, date: Optional[str] = None):
    """Energy waterfall: clear-sky potential → − clouds → − heat → − faults → − not measured → − other = actual.
    One plant and day, one plant's whole period (no date), or both plants' whole period (no plant)."""
    store = _weather_store()
    metrics = store.metrics["breakdown"]
    if plant is None:
        if date is not None:
            raise HTTPException(400, "Choose a plant when asking for one day's waterfall.")
        totals, label = metrics["total"], "both plants, whole period"
    else:
        plant = store.check_plant(plant)
        if date is None:
            totals, label = metrics["by_plant"][f"plant_{plant}"], f"Plant {plant}, whole period"
        else:
            date = store.check_date(date, plant)
            totals, label = _one_day(store.breakdown, plant, date), f"Plant {plant}, {date}"
    steps = _waterfall(totals)
    losses = _loss_totals(steps)
    return {"plant": plant, "date": date, "label": label, "steps": steps, **losses,
            "fixable_loss_inr": round(losses["fixable_loss_kwh"] * config.TARIFF_INR_PER_KWH, 0),
            "summary": totals["summary"] if date is not None else None,
            "method": metrics["method"], "tariff_note": store.metrics["losses"]["tariff_note"]}
