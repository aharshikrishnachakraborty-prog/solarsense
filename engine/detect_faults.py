"""Detect faults with simple, explainable rules and turn them into alerts (Phase 4).

Run from the solarsense folder with:   python -m engine.detect_faults
Reads data/processed/expected.parquet, writes data/processed/alerts.parquet.
All thresholds live in engine/config.py.
"""

import json

import numpy as np
import pandas as pd

from engine import config
from engine.alert_text import RECOMMENDED_ACTIONS, make_reason, make_severity
from engine.metrics import load_metrics, save_metrics_section

INTERVAL = pd.Timedelta(minutes=15)
TYPE_CODES = {"INVERTER_TRIP": "TRIP", "UNDERPERFORMANCE": "UNDER", "DEGRADATION": "DEGR",
              "DATA_GAP": "GAP", "OVERHEATING": "HEAT", "SENSOR_ISSUE": "SENS"}


def add_interval_flags(table):
    """Mark every 15-minute daylight row that breaks a trip, underperformance or gap rule."""
    present = ~table["is_missing"]
    table["trip_flag"] = (present & (table["irradiation"] >= config.TRIP_IRRADIATION_MIN)
                          & (table["ac_kw"] <= config.TRIP_AC_MAX_KW))
    # A trip already explains low output, so it is not ALSO counted as underperformance.
    table["under_flag"] = (present & ~table["trip_flag"]
                           & (table["residual_pct"] <= config.UNDER_RESIDUAL_PCT_MAX)
                           & (table["peer_ratio"] <= config.UNDER_PEER_RATIO_MAX))
    table["gap_flag"] = table["is_missing"]
    # Share of the plant's inverters tripped at each moment (used in trip reasons).
    tripped = table.groupby(["plant", "timestamp"])["trip_flag"].agg(["sum", "count"])
    table = table.join(tripped, on=["plant", "timestamp"])
    table["others_down_pct"] = 100 * (table["sum"] - table["trip_flag"]) / (table["count"] - 1)
    return table.drop(columns=["sum", "count"])


def find_events(rows, flag_column, min_intervals, blocker_column=None):
    """Group flagged readings of one inverter (or plant) into events of consecutive time.

    blocker_column: readings an event may NOT stretch across (e.g. an underperformance
    event must not bridge a tripped reading — the trip takes priority).
    """
    rows = rows.sort_values("timestamp")
    flagged = rows.loc[rows[flag_column], "timestamp"]
    if flagged.empty:
        return []
    # A new event starts when the gap to the previous flagged reading is too big...
    max_step = INTERVAL * (1 + config.MERGE_GAP_INTERVALS)
    new_event = flagged.diff() > max_step
    # ...or when a blocking reading lies in between.
    if blocker_column is not None:
        blockers_so_far = rows[blocker_column].cumsum()[rows[flag_column]]
        new_event |= blockers_so_far.diff() > 0
    event_number = new_event.cumsum()
    events = []
    for _, times in flagged.groupby(event_number):
        if len(times) >= min_intervals:
            start, end = times.iloc[0], times.iloc[-1]
            events.append({"start": start, "end": end + INTERVAL, "intervals": int(len(times)),
                           "rows": rows[(rows["timestamp"] >= start) & (rows["timestamp"] <= end)]})
    return events


def energy_numbers(rows):
    """Confirmed loss (kWh) on readings we have, and expected energy at risk where readings are missing."""
    present = rows[~rows["is_missing"]]
    shortfall = (present["expected_kw"] - present["ac_kw"]).clip(lower=0)
    return {"energy_loss_kwh": round(float(shortfall.sum() * config.INTERVAL_HOURS), 1),
            "energy_at_risk_kwh": round(float(rows.loc[rows["is_missing"], "expected_kw"].sum()
                                              * config.INTERVAL_HOURS), 1)}


def interval_alerts(table, fault_type, flag_column, min_intervals, blocker_column=None):
    """Build trip / underperformance / data-gap events for every inverter."""
    events = []
    for (plant, inverter), rows in table.groupby(["plant", "inverter"]):
        for event in find_events(rows, flag_column, min_intervals, blocker_column):
            flagged = event["rows"][event["rows"][flag_column]]
            evidence = {"intervals": event["intervals"],
                        "duration_hours": (event["end"] - event["start"]) / pd.Timedelta(hours=1),
                        "avg_irradiation": round(float(flagged["irradiation"].mean()), 3),
                        "avg_actual_kw": round(float(flagged["ac_kw"].mean()), 1) if fault_type != "DATA_GAP" else None,
                        "avg_expected_kw": round(float(flagged["expected_kw"].mean()), 1),
                        "avg_residual_pct": round(float(flagged["residual_pct"].mean()), 1),
                        "avg_peer_ratio": round(float(flagged["peer_ratio"].mean()), 3),
                        "others_down_pct": round(float(flagged["others_down_pct"].mean()), 1)}
            evidence.update(energy_numbers(flagged))
            events.append({"plant": plant, "inverter": inverter, "fault_type": fault_type,
                           "start": event["start"], "end": event["end"], "evidence": evidence})
    return events


def degradation_alerts(table):
    """Find inverters whose daily performance vs neighbours declines steadily (dust, ageing)."""
    usable = table[~table["is_missing"] & ~table["trip_flag"]
                   & (table["expected_kw"] >= config.MIN_EXPECTED_KW_FOR_RATIO)]
    daily = usable.groupby(["plant", "inverter", "date"])[["ac_kw", "expected_kw"]].sum().reset_index()
    daily["pr"] = daily["ac_kw"] / daily["expected_kw"]
    # Relative to the plant median that day, so weather and plant-wide effects cancel out.
    daily["relative_pr"] = daily["pr"] / daily.groupby(["plant", "date"])["pr"].transform("median")

    events = []
    for (plant, inverter), days in daily.groupby(["plant", "inverter"]):
        if len(days) < config.DEGRADATION_MIN_DAYS:
            continue
        day_number = (pd.to_datetime(days["date"]) - pd.to_datetime(days["date"].iloc[0])).dt.days
        slope, intercept = np.polyfit(day_number, days["relative_pr"], 1)   # straight-line fit
        fitted = intercept + slope * day_number
        decline_pct = 100 * (fitted.iloc[0] - fitted.iloc[-1])
        if 100 * slope > config.DEGRADATION_SLOPE_MAX_PCT or decline_pct < config.DEGRADATION_MIN_TOTAL_DECLINE_PCT:
            continue
        # Loss = each day's expected energy × how far performance has dropped since the start.
        expected_kwh = days["expected_kw"] * config.INTERVAL_HOURS
        lost_kwh = (expected_kwh * (fitted.iloc[0] - fitted).clip(lower=0)).sum()
        start, end = pd.Timestamp(days["date"].iloc[0]), pd.Timestamp(days["date"].iloc[-1]) + pd.Timedelta(days=1)
        evidence = {"days": int(len(days)), "duration_hours": (end - start) / pd.Timedelta(hours=1),
                    "slope_pct_per_day": round(float(100 * slope), 3),
                    "start_relative_pct": round(float(100 * fitted.iloc[0]), 1),
                    "end_relative_pct": round(float(100 * fitted.iloc[-1]), 1),
                    "total_decline_pct": round(float(decline_pct), 1),
                    "energy_loss_kwh": round(float(lost_kwh), 1),
                    "energy_at_risk_kwh": 0.0}
        events.append({"plant": plant, "inverter": inverter, "fault_type": "DEGRADATION",
                       "start": start, "end": end, "evidence": evidence})
    return events


def overheating_alerts(table):
    """Plant-level: very hot panels while the whole plant underperforms (one temperature sensor per plant)."""
    events = []
    for plant, rows in table.groupby("plant"):
        moments = rows.groupby("timestamp").agg(
            module_temp=("module_temp", "first"), ambient_temp=("ambient_temp", "first"),
            plant_ratio=("peer_median_ratio", "first"), expected_kw=("expected_kw", "sum")).reset_index()
        moments["temp_delta"] = moments["module_temp"] - moments["ambient_temp"]
        moments["heat_flag"] = ((moments["temp_delta"] >= config.OVERHEAT_DELTA_MIN_C)
                                & (moments["plant_ratio"] <= config.OVERHEAT_PLANT_RATIO_MAX))
        for event in find_events(moments, "heat_flag", config.OVERHEAT_MIN_INTERVALS):
            hot = event["rows"][event["rows"]["heat_flag"]]
            evidence = {"intervals": event["intervals"],
                        "duration_hours": (event["end"] - event["start"]) / pd.Timedelta(hours=1),
                        "avg_temp_delta_c": round(float(hot["temp_delta"].mean()), 1),
                        "avg_module_temp_c": round(float(hot["module_temp"].mean()), 1),
                        "avg_plant_ratio": round(float(hot["plant_ratio"].mean()), 3),
                        "energy_loss_kwh": round(float((hot["expected_kw"] * (1 - hot["plant_ratio"])).sum()
                                                       * config.INTERVAL_HOURS), 1),
                        "energy_at_risk_kwh": 0.0}
            events.append({"plant": plant, "inverter": "ALL", "fault_type": "OVERHEATING",
                           "start": event["start"], "end": event["end"], "evidence": evidence})
    return events


def sensor_issue_alerts(table):
    """Plant-level data/sensor problems measured in Phases 1–2 (impossible or broken readings)."""
    metrics = load_metrics()
    data, cleaning = metrics["data"]["plants"], metrics["cleaning"]
    events = []
    for plant, rows in table.groupby("plant"):
        start, end = rows["timestamp"].min().normalize(), rows["timestamp"].max().normalize() + pd.Timedelta(days=1)
        p = data[f"plant_{plant}"]
        issues = []
        if plant == config.DC_SUSPECT_PLANT:
            issues.append(("Medium", f"DC_POWER readings are about {cleaning['dc_scale_factor']}× too large (AC÷DC "
                           f"was {p['ac_dc_ratio_median']}, physically impossible). Corrected in our pipeline, "
                           "but the DC meter/logger should be recalibrated."))
        if p["total_yield_drops"] > 0 or p["total_yield_zero_rows"] > 0:
            issues.append(("Low", f"The lifetime energy counter (TOTAL_YIELD) is broken: {p['total_yield_zero_rows']:,} "
                           f"readings are 0 and it goes backwards {p['total_yield_drops']:,} times."))
        if p["daily_yield_drops_in_daylight"] > 0:
            issues.append(("Low", f"The daily energy counter (DAILY_YIELD) goes backwards "
                           f"{p['daily_yield_drops_in_daylight']:,} times while the sun is up."))
        if p["ac_greater_than_dc_rows"] > 0:
            issues.append(("Low", f"{p['ac_greater_than_dc_rows']} readings show AC power above DC power "
                           f"(up to {p['ac_greater_than_dc_max_excess_pct']}% above), which is impossible."))
        for severity, description in issues:
            evidence = {"description": description, "severity": severity,
                        "duration_hours": (end - start) / pd.Timedelta(hours=1),
                        "energy_loss_kwh": 0.0, "energy_at_risk_kwh": 0.0}
            events.append({"plant": plant, "inverter": "ALL", "fault_type": "SENSOR_ISSUE",
                           "start": start, "end": end, "evidence": evidence})
    return events


def events_to_alerts(events):
    """Give every event an id, severity, reason and action; return one alerts table."""
    alerts = pd.DataFrame(events).sort_values(["plant", "fault_type", "start", "inverter"], ignore_index=True)
    alerts["id"] = [f"P{plant}-{TYPE_CODES[ftype]}-{n + 1:04d}" for plant, ftype, n in
                    zip(alerts["plant"], alerts["fault_type"], alerts.groupby(["plant", "fault_type"]).cumcount())]
    alerts["duration_hours"] = [round(ev["duration_hours"], 2) for ev in alerts["evidence"]]
    alerts["severity"] = [make_severity(t, ev) for t, ev in zip(alerts["fault_type"], alerts["evidence"])]
    alerts["reason"] = [make_reason(t, ev) for t, ev in zip(alerts["fault_type"], alerts["evidence"])]
    alerts["energy_loss_kwh"] = [ev["energy_loss_kwh"] for ev in alerts["evidence"]]
    alerts["energy_at_risk_kwh"] = [ev["energy_at_risk_kwh"] for ev in alerts["evidence"]]
    alerts["recommended_action"] = alerts["fault_type"].map(RECOMMENDED_ACTIONS)
    alerts["status"] = "Open"
    alerts["evidence"] = [json.dumps(ev) for ev in alerts["evidence"]]   # stored as text in parquet
    return alerts[["id", "plant", "inverter", "fault_type", "start", "end", "duration_hours", "severity",
                   "energy_loss_kwh", "energy_at_risk_kwh", "reason", "evidence", "recommended_action", "status"]]


def detect_inverter_events(table):
    """All per-inverter rules on a flagged table. Also used by validate.py on injected data."""
    return (interval_alerts(table, "INVERTER_TRIP", "trip_flag", config.TRIP_MIN_INTERVALS)
            + interval_alerts(table, "UNDERPERFORMANCE", "under_flag", config.UNDER_MIN_INTERVALS,
                              blocker_column="trip_flag")
            + interval_alerts(table, "DATA_GAP", "gap_flag", config.GAP_MIN_INTERVALS)
            + degradation_alerts(table))


def detect_all():
    """Run every rule on both plants, save alerts.parquet and alert counts in metrics.json."""
    if not config.EXPECTED_FILE.exists():
        raise FileNotFoundError("expected.parquet not found — run: python -m engine.expected_model")
    table = add_interval_flags(pd.read_parquet(config.EXPECTED_FILE))
    events = detect_inverter_events(table) + overheating_alerts(table) + sensor_issue_alerts(table)
    alerts = events_to_alerts(events)
    alerts.to_parquet(config.ALERTS_FILE, index=False)

    counts = {"total": int(len(alerts)),
              "by_type": alerts["fault_type"].value_counts().to_dict(),
              "by_severity": alerts["severity"].value_counts().to_dict(),
              "by_plant_and_type": {f"plant_{p}": g["fault_type"].value_counts().to_dict()
                                    for p, g in alerts.groupby("plant")},
              "inverters_with_alerts": {f"plant_{p}": int(g.loc[g["inverter"] != "ALL", "inverter"].nunique())
                                        for p, g in alerts.groupby("plant")}}
    counts["by_type"] = {k: int(v) for k, v in counts["by_type"].items()}
    counts["by_severity"] = {k: int(v) for k, v in counts["by_severity"].items()}
    counts["by_plant_and_type"] = {p: {k: int(v) for k, v in d.items()} for p, d in counts["by_plant_and_type"].items()}
    save_metrics_section("alerts", counts)
    return alerts, counts


if __name__ == "__main__":
    all_alerts, alert_counts = detect_all()
    print(f"Saved {len(all_alerts)} alerts to {config.ALERTS_FILE}")
    print(json.dumps({k: alert_counts[k] for k in ["by_type", "by_severity", "inverters_with_alerts"]}, indent=2))
