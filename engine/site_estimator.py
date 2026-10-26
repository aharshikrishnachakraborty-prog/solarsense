"""Solar Site Planner (Phase 12): how much energy would a solar plant make at ANY place in India?

Run from the solarsense folder:   python -m engine.site_estimator

1. Ask NASA POWER (free, no key) for the last 12 complete months of daily sunlight and air temperature there.
2. Energy per day = plant size × sunlight × (1 − system losses) × inverter efficiency
                    × (1 + temperature coefficient × (panel temperature − 25 °C)).
3. The temperature part reuses what WE measured on the Kaggle plants (Phase W2): how much power each extra °C
   costs, and how much hotter than the air the panels get in the sun. Losses we cannot measure are ASSUMPTIONS.
This shows the engine can plan a brand-new plant anywhere — not only the two plants in our data.
"""

import calendar
import json
from datetime import date, timedelta

import pandas as pd
import requests

from engine import config
from engine.assumptions import record_assumption
from engine.metrics import load_metrics, save_metrics_section
from engine.weather_text import indian


class SiteDataUnavailable(Exception):
    """NASA POWER could not be reached and nothing is saved on disk for this place."""


def last_full_months(today=None):
    """First and last day of the last 12 complete months that NASA has surely published."""
    today = today or date.today()
    ready = today - timedelta(days=config.NASA_POWER_DELAY_DAYS)
    end = ready.replace(day=1) - timedelta(days=1)               # last day of the month before `ready`
    start_month = (end.year * 12 + end.month - 1) - (config.SITE_MONTHS - 1)
    return date(start_month // 12, start_month % 12 + 1, 1), end


def cache_path(lat, lon, start, end):
    """Where one NASA answer is saved, e.g. data/external/nasa_power/28.61_77.21_20251001_20260930.json."""
    return config.NASA_CACHE_DIR / f"{lat:.2f}_{lon:.2f}_{start:%Y%m%d}_{end:%Y%m%d}.json"


def fetch_nasa_power(lat, lon, start, end):
    """NASA's daily values for this place and period: from the disk cache, else from the internet (10 s limit),
    else the newest saved period for this place. Returns (payload, where_it_came_from)."""
    path = cache_path(lat, lon, start, end)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), "saved copy"
    params = {"parameters": ",".join(config.NASA_POWER_PARAMETERS), "community": "RE", "format": "JSON",
              "latitude": f"{lat:.2f}", "longitude": f"{lon:.2f}", "start": f"{start:%Y%m%d}", "end": f"{end:%Y%m%d}"}
    try:
        response = requests.get(config.NASA_POWER_URL, params=params, timeout=config.NASA_POWER_TIMEOUT_S)
        response.raise_for_status()
        payload = {"lat": round(lat, 2), "lon": round(lon, 2), "start": f"{start:%Y-%m-%d}",
                   "end": f"{end:%Y-%m-%d}", "parameter": response.json()["properties"]["parameter"]}
    except (requests.RequestException, ValueError, KeyError) as error:
        older = sorted(config.NASA_CACHE_DIR.glob(f"{lat:.2f}_{lon:.2f}_*.json"))
        if older:   # offline, but this place was asked before: use the newest saved year
            return json.loads(older[-1].read_text(encoding="utf-8")), "older saved copy (NASA unreachable)"
        raise SiteDataUnavailable("NASA POWER could not be reached (no internet?) and this location has no saved "
                                  "data yet. Try a preset city, or try again when online.") from error
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload, "NASA POWER (just downloaded)"


def daily_table(payload):
    """One row per day: sunlight (kWh/m²/day) and air temperature (°C); NASA's −999 'no value' becomes empty."""
    sunlight, air = (payload["parameter"][name] for name in config.NASA_POWER_PARAMETERS)
    days = pd.DataFrame({"day": pd.to_datetime(list(sunlight), format="%Y%m%d"),
                         "sunlight": list(sunlight.values()), "air_temp": [air.get(key) for key in sunlight]})
    for column in ["sunlight", "air_temp"]:
        days[column] = pd.to_numeric(days[column]).where(lambda v: v > config.NASA_POWER_MISSING + 1)
    return days


def calibrate(dates=None):
    """Measure, from our Kaggle weather data, how a day's sunlight total turns into panel temperature.
    `dates` limits it to some days (the accuracy backtest calibrates on training days only)."""
    plant = config.SITE_CALIBRATION_PLANT
    rows = pd.read_parquet(config.WEATHER_15MIN_FILE)
    rows = rows[(rows["plant"] == plant) & ~rows["weather_missing"]]
    if dates is not None:
        rows = rows[rows["date"].astype(str).isin(dates)]
    days = []
    for _, day in rows.groupby("date"):
        sun = day["irradiation"].clip(lower=0)
        if len(day) < config.SITE_CALIBRATION_MIN_READINGS or sun.sum() == 0:
            continue   # incomplete days would bias the averages
        days.append({"sunlit_hours": sun.sum() * 0.25 / ((sun ** 2).sum() / sun.sum()),
                     "air_offset": (day["ambient_temp"] * sun).sum() / sun.sum() - day["ambient_temp"].mean()})
    days = pd.DataFrame(days)
    heat = load_metrics()["temperature"]["by_plant"][f"plant_{plant}"]
    return {"plant": plant, "days_used": len(days),
            # Daily sunlight ÷ this = the typical sunlight strength (kW/m²) while the panels produce.
            "effective_sun_hours": round(float(days["sunlit_hours"].mean()), 2),
            # While the panels produce, the air is this much warmer than its 24-hour average (NASA gives the average).
            "daytime_air_offset_c": round(float(days["air_offset"].mean()), 2),
            "temp_coef_pct_per_c": heat["coefficient_used_pct_per_c"],
            "heating_c_per_kw_m2": heat["panel_heating"]["heating_c_per_kw_m2"],
            "heating_at_zero_sun_c": heat["panel_heating"]["heating_at_zero_sun_c"]}


def system_factor():
    """Share of the panels' energy left after system losses and the inverter (both ASSUMPTIONS)."""
    return (1 - config.SITE_SYSTEM_LOSSES_PCT / 100) * config.SITE_INVERTER_EFFICIENCY_PCT / 100


def add_daily_energy(days, capacity_kw, cal):
    """Add each day's panel temperature and expected kWh (the formula in the module docstring)."""
    days = days.copy()
    days["panel_temp"] = (days["air_temp"] + cal["daytime_air_offset_c"] + cal["heating_at_zero_sun_c"]
                          + cal["heating_c_per_kw_m2"] * days["sunlight"] / cal["effective_sun_hours"])
    days["kwh_at_25c"] = capacity_kw * days["sunlight"] * system_factor()
    days["kwh"] = days["kwh_at_25c"] * (1 + cal["temp_coef_pct_per_c"] / 100 * (days["panel_temp"] - 25))
    return days


def estimate_from_daily(days, capacity_kw, cal):
    """Expected kWh per month for a plant of this size, using the formula in the module docstring."""
    days = add_daily_energy(days, capacity_kw, cal)
    months = []
    for month, group in days.groupby(days["day"].dt.to_period("M")):
        valid = group.dropna(subset=["kwh"])
        length = calendar.monthrange(month.year, month.month)[1]
        months.append({"month": str(month), "label": month.strftime("%b %Y"), "days_used": len(valid),
                       "days_missing": length - len(valid),
                       "sunlight_kwh_m2_day": round(float(valid["sunlight"].mean()), 2),
                       "air_temp_c": round(float(valid["air_temp"].mean()), 1),
                       "panel_temp_c": round(float((valid["panel_temp"] * valid["sunlight"]).sum()
                                                   / valid["sunlight"].sum()), 1),
                       # Missing days are filled with the month's average day.
                       "expected_kwh": round(float(valid["kwh"].mean()) * length, 0),
                       "kwh_at_25c": round(float(valid["kwh_at_25c"].mean()) * length, 0)})
    return months


def estimate_site(lat, lon, capacity_kw, cal, today=None):
    """The full answer for one place and plant size: monthly kWh, yearly total, heat cost and an honest note."""
    lat, lon = round(float(lat), 2), round(float(lon), 2)
    start, end = last_full_months(today)
    payload, data_from = fetch_nasa_power(lat, lon, start, end)
    months = estimate_from_daily(daily_table(payload), capacity_kw, cal)
    yearly = sum(m["expected_kwh"] for m in months)
    at_25c = sum(m["kwh_at_25c"] for m in months)
    best = max(months, key=lambda m: m["expected_kwh"])
    worst = min(months, key=lambda m: m["expected_kwh"])
    result = {"lat": lat, "lon": lon, "capacity_kw": capacity_kw, "period_start": payload["start"],
              "period_end": payload["end"], "data_from": data_from, "months": months, "yearly_kwh": yearly,
              "specific_yield_kwh_per_kw": round(yearly / capacity_kw, 0),
              "heat_loss_pct": round(100 * (at_25c - yearly) / at_25c, 1) if at_25c else None,
              "best_month": best["label"], "worst_month": worst["label"],
              "days_missing": sum(m["days_missing"] for m in months), "assumptions": assumption_list(cal),
              "uncertainty_note": uncertainty_note(payload)}
    result["takeaway"] = (f"A {indian(capacity_kw)} kW plant at {lat}°N, {lon}°E would make about "
                          f"{indian(yearly)} kWh a year ({indian(result['specific_yield_kwh_per_kw'])} kWh per kW) — "
                          f"most in {best['label']}, least in {worst['label']}. Hot panels cost about "
                          f"{result['heat_loss_pct']}% of it.")
    return result


def assumption_list(cal):
    """Every number the estimate rests on, with where it comes from (shown on the web page)."""
    plant = f"Plant {cal['plant']}"
    return [
        {"name": "System losses (dust, wiring, mismatch)", "value": config.SITE_SYSTEM_LOSSES_PCT, "unit": "%",
         "source": "ASSUMPTION — NREL PVWatts default"},
        {"name": "Inverter efficiency", "value": config.SITE_INVERTER_EFFICIENCY_PCT, "unit": "%",
         "source": "ASSUMPTION — NREL PVWatts default"},
        {"name": "Power lost per °C of panel heat", "value": cal["temp_coef_pct_per_c"], "unit": "%/°C",
         "source": f"Measured on {plant} (Phase W2)"},
        {"name": "Panel heating in full sun", "value": cal["heating_c_per_kw_m2"], "unit": "°C per kW/m²",
         "source": f"Measured on {plant} (Phase W2)"},
        {"name": "Effective sunny hours per day", "value": cal["effective_sun_hours"], "unit": "h",
         "source": f"Measured on {plant}'s sunlight sensor"},
        {"name": "Daytime air warmer than the daily average by", "value": cal["daytime_air_offset_c"], "unit": "°C",
         "source": f"Measured on {plant}'s air sensor"}]


def uncertainty_note(payload):
    """Plain words on how far to trust the estimate."""
    return (f"Planning estimate, not a guarantee. It uses NASA satellite data for {payload['start']} to "
            f"{payload['end']} (daily, averaged over a grid cell tens of km wide, so local haze or shade is not "
            "seen), assumes flat panels (tilting them towards the sun usually gives more), uses typical system "
            "losses instead of a real design, and reuses the heat behaviour measured on one Kaggle plant. "
            "Another year's weather will differ.")


def record_site_assumptions():
    """Write the site estimator's loss assumption to assumptions.md."""
    record_assumption(
        key="site_system_losses", title="Solar Site Planner: losses we cannot measure",
        value=f"{config.SITE_SYSTEM_LOSSES_PCT} / {config.SITE_INVERTER_EFFICIENCY_PCT}",
        unit="% system losses / % inverter efficiency",
        why=("A new site has no design yet (and the Kaggle data has no plant capacity), so dust, wiring, mismatch "
             "and inverter losses cannot be measured. We use NREL PVWatts' published defaults. Temperature is NOT "
             "in these numbers: it uses our measured coefficient. Panels are assumed flat."),
        source="NREL PVWatts default losses; configurable in engine/config.py (SITE_SYSTEM_LOSSES_PCT)")


def build_site_estimator(today=None):
    """Measure the calibration, estimate the 3 preset cities (skipped if offline) → metrics.json."""
    cal = calibrate()
    presets = {}
    for city in config.SITE_PRESETS:
        try:
            result = estimate_site(city["lat"], city["lon"], config.SITE_DEFAULT_CAPACITY_KW, cal, today)
        except SiteDataUnavailable as error:
            print(f"  {city['name']}: skipped — {error}")
            continue
        presets[city["name"]] = {key: result[key] for key in ["lat", "lon", "capacity_kw", "period_start",
                                                              "period_end", "yearly_kwh", "specific_yield_kwh_per_kw",
                                                              "heat_loss_pct", "best_month", "worst_month"]}
        print(f"  {city['name']}: {result['takeaway']}")
    save_metrics_section("site_estimator", {"calibration": cal, "presets": presets,
                                            "system_losses_pct": config.SITE_SYSTEM_LOSSES_PCT,
                                            "inverter_efficiency_pct": config.SITE_INVERTER_EFFICIENCY_PCT})
    record_site_assumptions()
    return cal, presets


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows terminals and ₹ / °
    build_site_estimator()
