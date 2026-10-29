"""Facts for the chat assistant: a day, week or whole-period summary of one plant.

Every number here is computed by our code from the pipeline files. The assistant (Google Gemini) only
turns these facts into sentences — it never calculates or invents numbers.
"""

import pandas as pd

from engine import config

PERIODS = ["day", "week", "month"]
WEEK_DAYS = 7


def period_window(dates, date, period):
    """The list of dates a period covers, ending at `date` (month = every day we have, ≤ 34 days)."""
    dates = sorted(dates)
    if period == "day":
        return [date]
    if period == "week":
        end = dates.index(date)
        return dates[max(0, end - WEEK_DAYS + 1): end + 1]
    return dates   # "month": the dataset only covers about one month, so this is the whole period


def energy_facts(daily, days):
    """Actual vs expected energy, performance and ₹ lost over the given days."""
    rows = daily[daily["date"].isin(days)]
    actual, expected = rows["actual_kwh"].sum(), rows["expected_kwh"].sum()
    best = rows.loc[rows["performance_ratio"].idxmax()] if len(rows) else None
    worst = rows.loc[rows["fault_loss_kwh"].idxmax()] if len(rows) else None
    return {
        "actual_kwh": round(float(actual), 1),
        "expected_kwh": round(float(expected), 1),
        "actual_vs_expected_pct": round(float(actual / expected * 100), 1) if expected else None,
        "fault_loss_kwh": round(float(rows["fault_loss_kwh"].sum()), 1),
        "fault_loss_inr": round(float(rows["fault_loss_inr"].sum()), 0),
        "at_risk_kwh": round(float(rows["at_risk_kwh"].sum()), 1),
        "best_day": None if best is None else {"date": best["date"], "actual_vs_expected_pct":
                                                round(float(best["performance_ratio"]) * 100, 1)},
        "worst_fault_day": None if worst is None or worst["fault_loss_kwh"] <= 0 else
            {"date": worst["date"], "fault_loss_kwh": round(float(worst["fault_loss_kwh"]), 1)},
    }


def worst_inverters(daily_inverter, days, top_n=3):
    """The inverters that lost the most energy to faults over the given days."""
    rows = daily_inverter[daily_inverter["date"].isin(days)]
    totals = rows.groupby("inverter")[["fault_loss_kwh", "fault_loss_inr"]].sum()
    totals = totals[totals["fault_loss_kwh"] > 0].nlargest(top_n, "fault_loss_kwh").round(1)
    return [{"inverter": inv, "fault_loss_kwh": float(r.fault_loss_kwh), "fault_loss_inr": float(r.fault_loss_inr)}
            for inv, r in totals.iterrows()]


def weather_facts(breakdown, weather_daily, days):
    """Where the energy went (clouds, heat, faults) and what the sky was like."""
    rows = breakdown[breakdown["date"].isin(days)]
    sky = weather_daily[weather_daily["date"].isin(days)]
    facts = {
        "lost_to_clouds_kwh": round(float(rows["cloud_loss_kwh"].sum()), 1),
        "lost_to_heat_kwh": round(float(rows["heat_loss_kwh"].sum()), 1),
        "lost_to_faults_kwh": round(float(rows["fault_loss_kwh"].sum()), 1),
        "sky_days": {k: int(v) for k, v in sky["dominant_sky"].value_counts().items()},
        "hottest_panel_c": round(float(sky["max_module_c"].max()), 1) if len(sky) else None,
    }
    if len(days) == 1 and len(sky):
        facts["sky_summary"] = sky["summary"].iloc[0]
    return facts


def alert_facts(alerts, plant, days, top_n=3):
    """Alerts that were active during the given days: counts by type/severity and the costliest ones."""
    start, end = pd.Timestamp(days[0]), pd.Timestamp(days[-1]) + pd.Timedelta(days=1)
    rows = alerts[(alerts["plant"] == plant) & (alerts["start"] < end) & (alerts["end"] > start)]
    top = rows.nlargest(top_n, "energy_loss_kwh")
    return {
        "total": int(len(rows)),
        "open": int((rows["status"] == "Open").sum()),
        "critical": int((rows["severity"] == "Critical").sum()),
        "by_type": {k: int(v) for k, v in rows["fault_type"].value_counts().items()},
        "costliest": [{"inverter": r.inverter, "fault_type": r.fault_type, "severity": r.severity,
                       "start": str(r.start)[:16], "energy_loss_kwh": round(float(r.energy_loss_kwh), 1),
                       "reason": r.reason, "recommended_action": r.recommended_action}
                      for r in top.itertuples()],
    }


def summarize(store, plant, date, period):
    """All the facts for one plant and one period, ending at `date`."""
    days = period_window(store.dates, date, period)
    facts = {
        "period": period,
        "from": days[0], "to": days[-1], "days": len(days),
        "energy": energy_facts(store.daily_plant[store.daily_plant["plant"] == plant], days),
        "worst_inverters": worst_inverters(store.daily_inverter[store.daily_inverter["plant"] == plant], days),
        "alerts": alert_facts(store.alerts_with_status(), plant, days),
    }
    if store.weather_ready:
        facts["weather"] = weather_facts(store.breakdown[store.breakdown["plant"] == plant],
                                         store.weather_daily[store.weather_daily["plant"] == plant], days)
    return facts


def all_facts(store, plant, date):
    """Day, week and whole-period facts in one package — what the assistant receives with each question."""
    return {
        "plant": plant,
        "selected_date": date,
        "data_covers": f"{store.dates[0]} to {store.dates[-1]} ({len(store.dates)} days)",
        "tariff_inr_per_kwh": config.TARIFF_INR_PER_KWH,
        "tariff_note": "ASSUMPTION: ₹ figures use an assumed tariff (configurable).",
        "summaries": {period: summarize(store, plant, date, period) for period in PERIODS},
    }
