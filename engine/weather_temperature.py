"""How much power does heat cost? (Phase W2 — called by engine/weather.py)

Solar panels make less electricity when they are hot. Datasheets say a typical silicon panel loses about
0.3–0.5% of its power for every °C above 25 °C. Here we MEASURE that number from our own data:
  efficiency = AC power ÷ sunlight  (how much power each unit of sunlight gives)
  → fit a straight line of efficiency against panel temperature
  → temperature coefficient = how much efficiency changes per +1 °C, as a % of the efficiency at 25 °C.
Then heat loss = how much more a 25 °C panel would have made than our model's expected power.
"""

import numpy as np
import pandas as pd

from engine import config
from engine.expected_model import is_obvious_outage
from engine.metrics import load_metrics
from engine.weather_text import describe_temperature

EXPECTED_COLUMNS = ["plant", "inverter", "timestamp", "date", "is_missing", "weather_missing", "ac_kw",
                    "expected_kw", "irradiation", "module_temp", "peer_ratio"]


def load_expected_rows():
    """Daylight inverter rows with expected power (from the Phase 3 model)."""
    if not config.EXPECTED_FILE.exists():
        raise FileNotFoundError("expected.parquet not found — run: python -m engine.expected_model")
    return pd.read_parquet(config.EXPECTED_FILE, columns=EXPECTED_COLUMNS)


def healthy_sunny_rows(rows):
    """Rows fit for measuring the coefficient: real reading, good sun, inverter in line with its neighbours."""
    healthy = (~rows["is_missing"] & ~rows["weather_missing"] & ~is_obvious_outage(rows)
               & (rows["irradiation"] >= config.TEMP_FIT_MIN_IRRADIATION)
               & ((rows["peer_ratio"] - 1).abs() <= config.TEMP_FIT_PEER_TOLERANCE))
    fit_rows = rows[healthy].copy()
    fit_rows["efficiency"] = fit_rows["ac_kw"] / fit_rows["irradiation"]
    # Divide by each inverter's own median, so a slightly bigger inverter doesn't look "more efficient".
    fit_rows["efficiency_norm"] = fit_rows["efficiency"] / fit_rows.groupby(
        ["plant", "inverter"])["efficiency"].transform("median")
    return fit_rows


def coefficient_from_sums(n, sx, sy, sxx, sxy):
    """Straight-line fit from running sums; returns the coefficient in %/°C (slope ÷ efficiency at 25 °C)."""
    slope = (n * sxy - sx * sy) / (n * sxx - sx ** 2)
    at_25c = (sy - slope * sx) / n          # x is (temperature − 25), so the intercept is the 25 °C efficiency
    return 100 * slope / at_25c


def day_sums(fit_rows):
    """Per-day sums needed for a line fit — lets the bootstrap refit 500 times in a blink."""
    x = fit_rows["module_temp"] - config.REFERENCE_PANEL_TEMP_C
    y = fit_rows["efficiency_norm"]
    parts = pd.DataFrame({"date": fit_rows["date"], "n": 1.0, "sx": x, "sy": y, "sxx": x * x, "sxy": x * y})
    return parts.groupby("date").sum()


def fit_coefficient(fit_rows):
    """Coefficient (%/°C) with a 95% range from a bootstrap over whole days (seed 42)."""
    sums = day_sums(fit_rows)
    estimate = coefficient_from_sums(*sums.sum().to_numpy())
    rng = np.random.default_rng(config.RANDOM_SEED)
    n_days = len(sums)
    picks = rng.integers(0, n_days, size=(config.TEMP_FIT_BOOTSTRAP_RUNS, n_days))
    weights = np.stack([np.bincount(pick, minlength=n_days) for pick in picks])   # times each day was drawn
    resampled = weights @ sums.to_numpy()                                          # one row of sums per run
    runs = coefficient_from_sums(*resampled.T)
    low, high = np.percentile(runs, [2.5, 97.5])
    return {"coefficient_pct_per_c": round(float(estimate), 3), "ci95_pct_per_c": [round(float(low), 3),
            round(float(high), 3)], "rows": int(len(fit_rows)), "days": int(n_days)}


def chart_summary(plant_fit):
    """Fitted straight line and average efficiency per 2 °C — what the charts draw (in % of usual efficiency)."""
    slope, at_25c = np.polyfit(plant_fit["module_temp"] - config.REFERENCE_PANEL_TEMP_C, plant_fit["efficiency_norm"], 1)
    width = config.TEMP_CHART_BIN_C
    centre = (plant_fit["module_temp"] // width) * width + width / 2
    binned = plant_fit.groupby(centre)["efficiency_norm"].agg(["mean", "size"])
    binned = binned[binned["size"] >= config.TEMP_CHART_MIN_BIN_READINGS]
    return {"fit_line": {"efficiency_at_25c_pct": round(float(100 * at_25c), 2),
                         "slope_pct_points_per_c": round(float(100 * slope), 4),
                         "temp_min_c": round(float(plant_fit["module_temp"].min()), 1),
                         "temp_max_c": round(float(plant_fit["module_temp"].max()), 1)},
            "binned": [{"temp_c": float(temp), "efficiency_pct": round(float(100 * row["mean"]), 2),
                        "readings": int(row["size"])} for temp, row in binned.iterrows()]}


def coefficient_by_band(fit_rows):
    """Robustness check: the same fit inside narrow sunlight bands (should stay negative if heat is the cause)."""
    edges = config.TEMP_FIT_IRRADIATION_BANDS
    result = {}
    for low, high in zip(edges[:-1], edges[1:]):
        band = fit_rows[(fit_rows["irradiation"] >= low) & (fit_rows["irradiation"] < high)]
        if len(band) > 100:
            result[f"{low}-{high}"] = round(float(coefficient_from_sums(*day_sums(band).sum().to_numpy())), 3)
    return result


def alert_cross_check(rows, plant):
    """Same fit, but 'healthy' = no alert from the LAST fault-detection run (if one exists). None if no alerts yet."""
    if not config.ALERTS_FILE.exists():
        return None
    alerts = pd.read_parquet(config.ALERTS_FILE)
    alerts = alerts[(alerts["plant"] == plant) & (alerts["fault_type"] != "SENSOR_ISSUE")]  # notices, not faults
    candidates = rows[(rows["plant"] == plant) & ~rows["is_missing"] & ~rows["weather_missing"]
                      & (rows["irradiation"] >= config.TEMP_FIT_MIN_IRRADIATION)]
    in_alert = np.zeros(len(candidates), dtype=bool)
    for alert in alerts.itertuples():
        hit = (candidates["timestamp"] >= alert.start) & (candidates["timestamp"] < alert.end)
        in_alert |= (hit & ((candidates["inverter"] == alert.inverter) | (alert.inverter == "ALL"))).to_numpy()
    clean_rows = candidates[~in_alert].copy()
    clean_rows["efficiency_norm"] = clean_rows["ac_kw"] / clean_rows["irradiation"]
    clean_rows["efficiency_norm"] /= clean_rows.groupby("inverter")["efficiency_norm"].transform("median")
    return round(float(coefficient_from_sums(*day_sums(clean_rows).sum().to_numpy())), 3)


def choose_coefficient(fitted):
    """Use our measured coefficient unless it is unbelievable; then fall back to the typical value (ASSUMPTION)."""
    low, high = config.BELIEVABLE_TEMP_COEF_RANGE
    if low <= fitted <= high:
        return fitted, "measured from our data"
    return config.FALLBACK_TEMP_COEF_PCT, "typical silicon value (ASSUMPTION — our fit was not believable)"


def verdict(fit, bands):
    """Honest sentence: is our coefficient close to the typical silicon range, and why it may differ."""
    typical_low, typical_high = config.TYPICAL_TEMP_COEF_RANGE
    low, high = fit["ci95_pct_per_c"]
    if typical_low <= fit["coefficient_pct_per_c"] <= typical_high:
        closeness = "Inside the typical crystalline-silicon range"
    elif high >= typical_low and low <= typical_high:
        closeness = "Close to the typical crystalline-silicon range (our 95% range overlaps it)"
    else:
        closeness = "Outside the typical crystalline-silicon range"
    falling = sum(value < 0 for value in bands.values())
    if falling * 2 > len(bands):
        robustness = (f"It holds up: in {falling} of {len(bands)} narrow sunlight bands, hotter panels still give "
                      "less power.")
    else:
        robustness = (f"It does NOT hold up well: in only {falling} of {len(bands)} narrow sunlight bands do hotter "
                      "panels give less power, so for this plant the number is weak evidence.")
    return (f"{closeness} ({typical_low} to {typical_high} %/°C). {robustness} Why it can differ from a datasheet: hot "
            "panels and strong sunlight happen at the same time, so the fit also picks up other midday effects (sun "
            "angle, inverter limits), and there is only one panel-temperature sensor for the whole plant.")


def heat_loss_15min(rows, coefficient_by_plant):
    """Plant-level heat loss per 15 minutes: power a 25 °C panel would make minus the model's expected power."""
    plant_rows = rows.groupby(["plant", "timestamp"]).agg(
        plant_expected_kw=("expected_kw", "sum"), plant_actual_kw=("ac_kw", "sum"),
        module_temp=("module_temp", "first")).reset_index()
    coefficient = plant_rows["plant"].map(coefficient_by_plant).abs() / 100
    excess_c = (plant_rows["module_temp"] - config.REFERENCE_PANEL_TEMP_C).clip(lower=0).fillna(0)
    # expected_kw already INCLUDES the heat effect: expected = P25 × (1 − share)  →  P25 = expected ÷ (1 − share).
    share_lost = coefficient * excess_c
    plant_rows["power_at_25c_kw"] = plant_rows["plant_expected_kw"] / (1 - share_lost)
    plant_rows["heat_loss_kw"] = plant_rows["power_at_25c_kw"] - plant_rows["plant_expected_kw"]
    return plant_rows.drop(columns="module_temp")


def panel_heating_fit(table, plant):
    """How much hotter than the air the panels get per unit of sunlight (straight line + R²)."""
    rows = table[(table["plant"] == plant) & (table["irradiation"] > config.DAYLIGHT_IRRADIATION_THRESHOLD)]
    rows = rows.dropna(subset=["irradiation", "module_temp", "ambient_temp"])
    heating = rows["module_temp"] - rows["ambient_temp"]
    slope, intercept = np.polyfit(rows["irradiation"], heating, 1)
    r2 = 1 - ((heating - (slope * rows["irradiation"] + intercept)) ** 2).sum() / ((heating - heating.mean()) ** 2).sum()
    return {"heating_c_per_kw_m2": round(float(slope), 2), "heating_at_zero_sun_c": round(float(intercept), 2),
            "heating_per_0_1_kw_m2_c": round(float(slope) / 10, 2), "r2": round(float(r2), 3),
            "max_heating_c": round(float(heating.max()), 1)}


def daily_temperature(table):
    """One row per plant and day: air and panel temperatures, hot hours and heat loss (kWh, ₹, %)."""
    rows = []
    for (plant, date), day in table.groupby(["plant", "date"]):
        measured = day.dropna(subset=["module_temp"])
        hottest = measured.loc[measured["module_temp"].idxmax()] if len(measured) else None
        heat_kwh = day["heat_loss_kw"].sum() * config.INTERVAL_HOURS
        at_25c_kwh = day["power_at_25c_kw"].sum() * config.INTERVAL_HOURS
        summary = {"plant": plant, "date": str(date),
                   "min_ambient_c": round(day["ambient_temp"].min(), 1), "max_ambient_c": round(day["ambient_temp"].max(), 1),
                   "max_module_c": round(hottest["module_temp"], 1) if hottest is not None else np.nan,
                   "max_module_time": hottest["timestamp"] if hottest is not None else pd.NaT,
                   "hot_hours": day["is_hot_hour"].sum() * config.INTERVAL_HOURS,
                   "energy_at_25c_kwh": round(at_25c_kwh, 1), "heat_loss_kwh": round(heat_kwh, 1),
                   "heat_loss_inr": round(heat_kwh * config.TARIFF_INR_PER_KWH, 0),
                   "heat_loss_pct": round(100 * heat_kwh / at_25c_kwh, 2) if at_25c_kwh > 0 else 0.0}
        summary["temperature_summary"] = describe_temperature(summary)
        rows.append(summary)
    return pd.DataFrame(rows)


def plant_metrics(rows, fit_rows, plant, fit, daily):
    """Everything about one plant's temperature effect, for metrics.json."""
    plant_fit = fit_rows[fit_rows["plant"] == plant]
    bands = coefficient_by_band(plant_fit)
    used, source = choose_coefficient(fit["coefficient_pct_per_c"])
    gamma = load_metrics().get("expected_model", {}).get(f"plant_{plant}", {}).get("physics_coefficients", {})
    days = daily[daily["plant"] == plant]
    hottest = days.loc[days["max_module_c"].idxmax()]
    costliest = days.loc[days["heat_loss_kwh"].idxmax()]
    return {**fit, **chart_summary(plant_fit), "by_sunlight_band_pct_per_c": bands, "verdict": verdict(fit, bands),
            "cross_check_no_alert_rows_pct_per_c": alert_cross_check(rows, plant),
            "physics_model_gamma_pct_per_c": round(-100 * gamma["gamma_per_degC"], 3) if gamma else None,
            "coefficient_used_pct_per_c": used, "coefficient_source": source,
            "hot_hours_total": float(days["hot_hours"].sum()),
            "heat_loss_kwh_total": round(float(days["heat_loss_kwh"].sum()), 0),
            "heat_loss_inr_total": round(float(days["heat_loss_inr"].sum()), 0),
            "heat_loss_pct_of_25c_energy": round(float(100 * days["heat_loss_kwh"].sum()
                                                       / days["energy_at_25c_kwh"].sum()), 2),
            "hottest_day": {"date": hottest["date"], "max_module_c": hottest["max_module_c"],
                            "summary": hottest["temperature_summary"]},
            "costliest_heat_day": {"date": costliest["date"], "heat_loss_kwh": costliest["heat_loss_kwh"],
                                   "summary": costliest["temperature_summary"]}}


def add_temperature(table):
    """Phase W2 for the weather table: measure the coefficient, add heat loss + hot hours, summarise per day.

    Returns (15-min table with new columns, daily temperature table, metrics section, rows used for the fit).
    """
    rows = load_expected_rows()
    fit_rows = healthy_sunny_rows(rows)
    fits = {plant: fit_coefficient(fit_rows[fit_rows["plant"] == plant]) for plant in config.PLANTS}
    used = {plant: choose_coefficient(fit["coefficient_pct_per_c"])[0] for plant, fit in fits.items()}
    heat = heat_loss_15min(rows, used)
    table = table.merge(heat, on=["plant", "timestamp"], how="left")
    power_columns = ["plant_expected_kw", "plant_actual_kw", "power_at_25c_kw", "heat_loss_kw"]
    table[power_columns] = table[power_columns].fillna(0)        # no daylight inverter rows = night = 0 kW
    table["is_hot_hour"] = table["module_temp"] >= config.HOT_MODULE_TEMP_C
    daily = daily_temperature(table)
    section = {"reference_panel_temp_c": config.REFERENCE_PANEL_TEMP_C,
               "typical_range_pct_per_c": list(config.TYPICAL_TEMP_COEF_RANGE),
               "hot_module_temp_c": config.HOT_MODULE_TEMP_C, "tariff_inr_per_kwh": config.TARIFF_INR_PER_KWH,
               "healthy_rows_rule": (f"real reading, sunlight ≥ {config.TEMP_FIT_MIN_IRRADIATION} kW/m², not an obvious "
                                     f"outage, within ±{config.TEMP_FIT_PEER_TOLERANCE:.0%} of neighbouring inverters"),
               "by_plant": {}}
    for plant in config.PLANTS:
        section["by_plant"][f"plant_{plant}"] = {**plant_metrics(rows, fit_rows, plant, fits[plant], daily),
                                                 "panel_heating": panel_heating_fit(table, plant)}
    return table, daily, section, fit_rows
