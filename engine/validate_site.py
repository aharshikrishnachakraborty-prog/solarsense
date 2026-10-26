"""How accurate is the Solar Site Planner? Three honest checks (Phase 12).

Run from the solarsense folder:   python -m engine.validate_site      (needs internet once; answers are saved)

1. Backtest on OUR plant: give the planner's daily method the real sunlight and air temperature of Plant 1, tune
   only its size on the first 70% of days, and compare with the energy really made on the last 30% (unseen days).
2. Independent cross-check: PVGIS (EU Joint Research Centre, free, no key) simulates the same flat plant with the
   same losses. We split any gap into "different sunlight data" and "different maths".
3. Year-to-year spread: the same estimate on 5 past years of NASA weather — another year's weather differs.
"""

import json
from datetime import date

import pandas as pd
import requests

from engine import config
from engine.metrics import load_metrics, save_metrics_section
from engine.site_estimator import (add_daily_energy, calibrate, daily_table, estimate_from_daily, fetch_nasa_power,
                                   system_factor)


def backtest():
    """Predict Plant 1's daily energy from daily sunlight + daily average air temperature (what NASA gives)."""
    plant = config.SITE_CALIBRATION_PLANT
    rows = pd.read_parquet(config.WEATHER_15MIN_FILE)
    rows = rows[(rows["plant"] == plant) & ~rows["weather_missing"]]
    days = rows.groupby("date").agg(sunlight=("irradiation", lambda s: s.clip(lower=0).sum() * 0.25),
                                    air_temp=("ambient_temp", "mean"), readings=("irradiation", "size")).reset_index()
    days["date"] = days["date"].astype(str)
    energy = pd.read_parquet(config.ENERGY_BREAKDOWN_FILE)
    energy = energy[energy["plant"] == plant].assign(date=lambda t: t["date"].astype(str))
    energy["dirty"] = (energy["fault_loss_kwh"] + energy["not_measured_kwh"]) / energy["actual_kwh"]
    days = days.merge(energy[["date", "actual_kwh", "dirty"]], on="date")
    all_dates = sorted(days["date"])
    train_dates = all_dates[:int(round(len(all_dates) * config.TRAIN_FRACTION))]   # same time split as the model
    days = days[(days["dirty"] <= config.SITE_BACKTEST_MAX_DIRTY_SHARE)
                & (days["readings"] >= config.SITE_CALIBRATION_MIN_READINGS)]
    days = add_daily_energy(days, 1.0, calibrate(train_dates))   # calibrated on training days only
    train, test = days[days["date"].isin(train_dates)], days[~days["date"].isin(train_dates)]
    # The only thing tuned: plant size (the Kaggle data has no capacity). Baseline: sunlight only, no heat effect.
    size = train["actual_kwh"].sum() / train["kwh"].sum()
    size_sun_only = train["actual_kwh"].sum() / train["sunlight"].sum()
    result = {"plant": plant, "train_days": len(train), "test_days": len(test),
              "test_period": f"{test['date'].min()} to {test['date'].max()}"}
    for name, predicted in [("planner", size * test["kwh"]), ("sunlight_only", size_sun_only * test["sunlight"])]:
        errors = 100 * (predicted - test["actual_kwh"]) / test["actual_kwh"]
        result[name] = {"daily_error_pct": round(float(errors.abs().mean()), 1),
                        "worst_day_error_pct": round(float(errors.abs().max()), 1),
                        "total_error_pct": round(float(100 * (predicted.sum() / test["actual_kwh"].sum() - 1)), 1)}
    return result


def pvgis(lat, lon):
    """PVGIS's yearly yield (kWh per kW) and sunlight (kWh/m²) for flat panels with OUR losses (saved to disk)."""
    loss = round(100 * (1 - system_factor()), 2)   # PVGIS 'loss' includes the inverter
    path = config.PVGIS_CACHE_DIR / f"{lat:.2f}_{lon:.2f}_loss{loss}.json"
    if not path.exists():
        params = {"lat": lat, "lon": lon, "peakpower": 1, "loss": loss, "angle": 0, "aspect": 0, "outputformat": "json"}
        response = requests.get(config.PVGIS_URL, params=params, timeout=config.PVGIS_TIMEOUT_S)
        response.raise_for_status()
        body = response.json()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"inputs": body["inputs"]["meteo_data"], "totals": body["outputs"]["totals"]["fixed"]}),
                        encoding="utf-8")
    saved = json.loads(path.read_text(encoding="utf-8"))
    meteo, totals = saved["inputs"], saved["totals"]
    return {"yield_kwh_per_kw": round(totals["E_y"], 0), "sunlight_kwh_m2": round(totals["H(i)_y"], 0),
            "weather_data": f"{meteo['radiation_db']} {meteo['year_min']}–{meteo['year_max']}", "loss_pct": loss,
            # PVGIS's own breakdown: light reflected off the glass (we do not model it) and heat (we do).
            "reflection_loss_pct": round(-float(totals["l_aoi"]), 1), "heat_loss_pct": round(-float(totals["l_tg"]), 1)}


def yearly_nasa(lat, lon, cal):
    """Our estimate (kWh per kW) and NASA sunlight (kWh/m²) for each past full year in SITE_SPREAD_YEARS."""
    first, last = config.SITE_SPREAD_YEARS
    payload, _ = fetch_nasa_power(lat, lon, date(first, 1, 1), date(last, 12, 31))
    months = pd.DataFrame(estimate_from_daily(daily_table(payload), 1.0, cal))
    months["year"] = months["month"].str[:4].astype(int)
    months["days"] = months["days_used"] + months["days_missing"]
    months["sunlight"] = months["sunlight_kwh_m2_day"] * months["days"]
    return months.groupby("year").agg(yield_kwh_per_kw=("expected_kwh", "sum"), sunlight_kwh_m2=("sunlight", "sum"))


def compare_city(city, cal):
    """PVGIS vs our method for one preset city, with the gap split into sunlight data vs maths."""
    lat, lon = city["lat"], city["lon"]
    years, reference = yearly_nasa(lat, lon, cal), pvgis(lat, lon)
    ours, sun = float(years["yield_kwh_per_kw"].mean()), float(years["sunlight_kwh_m2"].mean())
    pct = lambda a, b: round(100 * (a / b - 1), 1)
    return {"ours_yield_kwh_per_kw": round(ours, 0), "ours_sunlight_kwh_m2": round(sun, 0),
            "ours_years": f"NASA POWER {config.SITE_SPREAD_YEARS[0]}–{config.SITE_SPREAD_YEARS[1]}",
            "pvgis": reference, "total_gap_pct": pct(ours, reference["yield_kwh_per_kw"]),
            "sunlight_gap_pct": pct(sun, reference["sunlight_kwh_m2"]),
            # Same sunlight in → how different is the energy out? (isolates the maths)
            "maths_gap_pct": pct(ours / sun, reference["yield_kwh_per_kw"] / reference["sunlight_kwh_m2"]),
            "pvgis_reflection_loss_pct": reference["reflection_loss_pct"],
            "yearly_yield_kwh_per_kw": {int(y): round(float(v), 0) for y, v in years["yield_kwh_per_kw"].items()},
            "year_spread_pct": round(float(100 * (years["yield_kwh_per_kw"].max() - years["yield_kwh_per_kw"].min())
                                           / years["yield_kwh_per_kw"].mean()), 1)}


def summary_sentence(back, cities):
    """One honest sentence for the page and the judges, built from the numbers above."""
    span = lambda key: sorted(abs(c[key]) for c in cities.values())
    total, sun, maths = span("total_gap_pct"), span("sunlight_gap_pct"), span("maths_gap_pct")
    glass = span("pvgis_reflection_loss_pct")
    spread = max(c["year_spread_pct"] for c in cities.values())
    return (f"Backtest on our plant ({back['test_days']} unseen days, real sunlight): daily energy within "
            f"{back['planner']['daily_error_pct']}% on average, {back['planner']['total_error_pct']:+}% in total. "
            f"Against the EU's PVGIS our yearly energy for the {len(cities)} cities differs by {total[0]}–{total[-1]}%: "
            f"NASA reports {sun[0]:.0f}–{sun[-1]:.0f}% less sunlight than PVGIS's weather data, while our maths gives "
            f"{maths[0]:.0f}–{maths[-1]:.0f}% more energy from the same sunlight (PVGIS also subtracts "
            f"{glass[0]}–{glass[-1]}% for light reflected off the glass, which we do not). "
            f"Weather alone changes a year by up to {spread}%.")


def validate_site():
    """Run all three checks and save them to metrics.json → "site_accuracy"."""
    cal = load_metrics()["site_estimator"]["calibration"]
    back = backtest()
    cities = {}
    for city in config.SITE_PRESETS:
        try:
            cities[city["name"]] = compare_city(city, cal)
        except (requests.RequestException, ValueError, KeyError) as error:
            print(f"  {city['name']}: skipped (offline?) — {error}")
    section = {"backtest": back, "cities": cities,
               "summary": summary_sentence(back, cities) if cities else None,
               "pvgis_note": "PVGIS = Photovoltaic Geographical Information System, EU Joint Research Centre (free, "
                             "no key); flat panels, same total losses as ours."}
    save_metrics_section("site_accuracy", section)
    print(json.dumps(section, indent=1, ensure_ascii=False))
    return section


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    validate_site()
