"""Read the sky condition (clear / cloudy) from the sunlight itself (Phase W1) and add the
temperature effect on power (Phase W2, in engine/weather_temperature.py).

Run from the solarsense folder with:   python -m engine.weather
- Writes data/processed/weather_15min.parquet (every 15 minutes) and weather_daily.parquet (one row per day)
- Saves "weather" (sky) and "temperature" (heat) sections in reports/metrics.json
- Draws reports/figures/weather_clear_vs_cloudy.png and temperature_vs_efficiency.png

How we "see" clouds without a cloud sensor:
  1. Clear-sky reference: for each time of day (e.g. 13:15), look at the sunlight at 13:15 on all 34 days
     and take a high percentile = "what a clear sky gives at 13:15". Smooth it into a bell curve.
  2. Clear-sky index (CSI) = actual sunlight ÷ clear-sky sunlight. 1.0 = clear, 0.5 = half the sun is blocked.
  3. Variability = how much the CSI jumps between readings. Passing clouds make the sunlight flicker.
ASSUMPTION: the reference is learned from our 34 days, not a physical sun model (the plant's GPS location is
not in the dataset). If every day at some time was cloudy, the reference would be too low at that time.
"""

import numpy as np
import pandas as pd

from engine import config
from engine.assumptions import record_assumption
from engine.metrics import save_metrics_section
from engine.weather_text import describe_day, dominant

def load_weather_readings():
    """One row per plant and 15-minute slot (the weather columns repeat for every inverter, so keep one copy)."""
    if not config.CLEAN_FILE.exists():
        raise FileNotFoundError("clean.parquet not found — run: python -m engine.clean_data")
    columns = ["plant", "timestamp", "date", "hour", "weather_missing", "irradiation", "ambient_temp", "module_temp"]
    readings = pd.read_parquet(config.CLEAN_FILE, columns=columns)
    readings = readings.drop_duplicates(["plant", "timestamp"]).sort_values(["plant", "timestamp"])
    # Slot 0 = 00:00, slot 1 = 00:15, ... slot 95 = 23:45 (the same time of day on every date).
    readings["slot"] = readings["timestamp"].dt.hour * 4 + readings["timestamp"].dt.minute // 15
    return readings.reset_index(drop=True)


def clear_sky_reference(readings):
    """For each plant and time of day: a high percentile of sunlight over all days, smoothed into a bell curve."""
    percentile = readings.groupby(["plant", "slot"])["irradiation"].quantile(config.CLEAR_SKY_PERCENTILE / 100)
    # Night slots are 0 on both ends of the day, so smoothing never mixes evening with morning.
    smooth = percentile.groupby(level="plant").transform(
        lambda curve: curve.rolling(config.CLEAR_SKY_SMOOTH_SLOTS, center=True, min_periods=1).mean())
    return smooth.rename("clear_sky_irr").reset_index()


def label_sky(csi, variability):
    """Turn clear-sky index + variability into one of the 4 sky labels (thresholds in config)."""
    steady = variability.fillna(0) <= config.VARIABILITY_CLEAR_MAX
    conditions = [(csi >= config.CSI_CLEAR_MIN) & steady,
                  csi >= config.CSI_PARTLY_MIN,           # includes "bright but flickering" readings
                  csi >= config.CSI_CLOUDY_MIN,
                  csi.notna()]
    labels = pd.Series(np.select(conditions, config.SKY_LABELS, default=""), index=csi.index)
    return labels.replace("", None)


def add_sky_columns(readings, reference):
    """Add clear_sky_irr, clear_sky_index, variability and sky_label to every 15-minute reading."""
    table = readings.merge(reference, on=["plant", "slot"], how="left")
    # "Sky readings": times of day when a clear sky would give real sunlight. Judged even if the actual
    # sunlight is ~0 — a dark midday is Overcast, not night.
    table["is_sky_reading"] = table["clear_sky_irr"] >= config.SKY_MIN_CLEAR_SKY_IRR
    csi = table["irradiation"] / table["clear_sky_irr"]
    table["clear_sky_index"] = csi.where(table["is_sky_reading"]).clip(*config.CSI_CLIP)
    # Variability: std of the reading-to-reading change in CSI, within one day only.
    window = config.VARIABILITY_WINDOW_SLOTS
    table["variability"] = table.groupby(["plant", "date"])["clear_sky_index"].transform(
        lambda day: day.diff().rolling(window, center=True, min_periods=2).std())
    table["sky_label"] = label_sky(table["clear_sky_index"], table["variability"])
    return table


def summarise_day(sky_rows):
    """One day's numbers: average CSI, % time per label, dominant label, sunshine score and sentence."""
    measured = sky_rows.dropna(subset=["clear_sky_index"])
    coverage_pct = 100 * len(measured) / len(sky_rows) if len(sky_rows) else 0.0
    # Sunshine score: the day's sunlight as a % of the clear-sky curve, using only readings we have.
    score = 100 * measured["irradiation"].sum() / measured["clear_sky_irr"].sum() if len(measured) else 0.0
    score = min(score, 100.0)
    shares = measured["sky_label"].value_counts(normalize=True).reindex(config.SKY_LABELS, fill_value=0) * 100
    summary = {"sky_readings": len(sky_rows), "coverage_pct": round(coverage_pct, 1),
               "avg_csi": round(measured["clear_sky_index"].mean(), 3) if len(measured) else np.nan,
               "sunlight_kwh_m2": round(measured["irradiation"].sum() * config.INTERVAL_HOURS, 3),
               "clear_sky_kwh_m2": round(measured["clear_sky_irr"].sum() * config.INTERVAL_HOURS, 3)}
    for label in config.SKY_LABELS:
        summary["pct_" + label.lower().replace(" ", "_")] = round(shares[label], 1)
    summary["dominant_sky"] = dominant(measured["sky_label"]) if len(measured) else None
    summary["sunshine_score"] = round(score, 1)
    summary["summary"] = describe_day(sky_rows, score, coverage_pct)
    return summary


def build_daily(table):
    """One row per plant and day, built from the sky readings."""
    rows = []
    for (plant, date), day in table[table["is_sky_reading"]].groupby(["plant", "date"]):
        rows.append({"plant": plant, "date": str(date), **summarise_day(day)})
    return pd.DataFrame(rows)


def blip_rate(labelled):
    """% of readings whose label differs from both neighbours while the neighbours agree (a one-reading flicker)."""
    blips = []
    for _, day in labelled.groupby("date"):
        labels = day["sky_label"].tolist()
        blips += [labels[i] != labels[i - 1] and labels[i - 1] == labels[i + 1] for i in range(1, len(labels) - 1)]
    return round(100 * float(np.mean(blips)), 1)


def sanity_checks(table, daily, plant):
    """Check the method makes sense: CSI ≈ 1 on the sunniest days and labels don't flicker randomly."""
    days = daily[(daily["plant"] == plant) & (daily["coverage_pct"] >= config.SKY_MIN_COVERAGE_PCT)]
    sunniest = days.nlargest(3, "sunshine_score")
    start_hour, end_hour = config.SANITY_MIDDAY_HOURS
    midday = table[(table["plant"] == plant) & table["date"].astype(str).isin(sunniest["date"])
                   & table["timestamp"].dt.hour.between(start_hour, end_hour - 1)]
    labelled = table[table["plant"] == plant].dropna(subset=["sky_label"])
    # Same labels shuffled randomly inside each day: what "random" flickering would look like.
    shuffled = labelled.copy()
    shuffled["sky_label"] = shuffled.groupby("date")["sky_label"].transform(
        lambda day: day.sample(frac=1, random_state=config.RANDOM_SEED).to_numpy())
    return {"avg_csi_3_sunniest_days": round(float(sunniest["avg_csi"].mean()), 3),
            "midday_median_csi_3_sunniest_days": round(float(midday["clear_sky_index"].median()), 3),
            "sunniest_days": sunniest["date"].tolist(),
            "single_reading_blips_pct": blip_rate(labelled),
            "single_reading_blips_pct_if_random": blip_rate(shuffled),
            "low_coverage_days": daily[(daily["plant"] == plant) &
                                       (daily["coverage_pct"] < config.SKY_MIN_COVERAGE_PCT)]["date"].tolist()}


def day_brief(row):
    """Small dictionary describing one day (for metrics.json)."""
    return {"date": row["date"], "sunshine_score": row["sunshine_score"], "avg_csi": row["avg_csi"],
            "dominant_sky": row["dominant_sky"], "summary": row["summary"]}


def build_metrics(table, daily):
    """The "weather" section of metrics.json: method settings, day counts per label and sanity checks."""
    result = {"method": {"clear_sky_percentile": config.CLEAR_SKY_PERCENTILE,
                         "clear_sky_smooth_slots": config.CLEAR_SKY_SMOOTH_SLOTS,
                         "csi_thresholds": {"clear_min": config.CSI_CLEAR_MIN, "partly_min": config.CSI_PARTLY_MIN,
                                            "cloudy_min": config.CSI_CLOUDY_MIN},
                         "variability_clear_max": config.VARIABILITY_CLEAR_MAX,
                         "note": "Clear-sky reference is learned from the 34 days (ASSUMPTION), not a physical model."},
              "by_plant": {}}
    for plant in config.PLANTS:
        days = daily[daily["plant"] == plant]
        trusted = days[days["coverage_pct"] >= config.SKY_MIN_COVERAGE_PCT]
        counts = days["dominant_sky"].value_counts().reindex(config.SKY_LABELS, fill_value=0)
        result["by_plant"][f"plant_{plant}"] = {
            "days": len(days),
            "days_by_dominant_sky": {label: int(n) for label, n in counts.items()},
            "avg_sunshine_score": round(days["sunshine_score"].mean(), 1),
            "sunniest_day": day_brief(trusted.loc[trusted["sunshine_score"].idxmax()]),
            "cloudiest_day": day_brief(trusted.loc[trusted["sunshine_score"].idxmin()]),
            "sanity": sanity_checks(table, daily, plant)}
    return result


def record_weather_assumptions(temperature):
    """Write the clear-sky and heat-loss assumptions to assumptions.md."""
    record_assumption(
        key="clear_sky_reference", title="Clear-sky sunlight learned from our own data",
        value=f"{config.CLEAR_SKY_PERCENTILE}th", unit="percentile per 15-min time of day",
        why=(f"No cloud sensor and no plant GPS location, so we cannot use a physical sun model. For each time "
             f"of day we take the {config.CLEAR_SKY_PERCENTILE}th percentile of sunlight over all 34 days "
             f"(smoothed over {config.CLEAR_SKY_SMOOTH_SLOTS} readings) as 'what a clear sky gives'. "
             "If a time of day was cloudy on almost every day, the reference there would be too low."),
        source="Computed from the data (engine/weather.py)")
    used = {plant: info["coefficient_used_pct_per_c"] for plant, info in temperature["by_plant"].items()}
    record_assumption(
        key="heat_loss_coefficient", title="Heat loss = power a 25 °C panel would make − expected power",
        value=" / ".join(f"{value}" for value in used.values()), unit="%/°C (Plant 1 / Plant 2, measured)",
        why=("Panels are rated at 25 °C. Each plant's temperature coefficient is measured from healthy, sunny rows "
             "(efficiency vs panel temperature, straight-line fit). Hot panels and strong sun happen together, so the "
             "coefficient is an estimate. If a fit is ever outside the believable range "
             f"{list(config.BELIEVABLE_TEMP_COEF_RANGE)} %/°C, the typical {config.FALLBACK_TEMP_COEF_PCT} %/°C is used."),
        source="Computed from the data (engine/weather_temperature.py); typical range from silicon panel datasheets")


def build_weather():
    """Run Phases W1 + W2: sky labels, then heat loss → files, metrics, assumptions, charts."""
    from engine.weather_report import plot_clear_vs_cloudy, plot_temperature_vs_efficiency   # matplotlib only here
    from engine.weather_temperature import add_temperature

    readings = load_weather_readings()
    reference = clear_sky_reference(readings)
    table = add_sky_columns(readings, reference)
    daily = build_daily(table)
    metrics = build_metrics(table, daily)
    table, daily_temperature, temperature, fit_rows = add_temperature(table)
    daily = daily.merge(daily_temperature, on=["plant", "date"], how="left")
    keep = ["plant", "timestamp", "date", "slot", "is_sky_reading", "weather_missing", "irradiation",
            "clear_sky_irr", "clear_sky_index", "variability", "sky_label", "ambient_temp", "module_temp",
            "is_hot_hour", "plant_expected_kw", "plant_actual_kw", "power_at_25c_kw", "heat_loss_kw"]
    table[keep].to_parquet(config.WEATHER_15MIN_FILE, index=False)
    daily.to_parquet(config.WEATHER_DAILY_FILE, index=False)
    save_metrics_section("weather", metrics)
    save_metrics_section("temperature", temperature)
    record_weather_assumptions(temperature)
    plot_clear_vs_cloudy(table, metrics)
    plot_temperature_vs_efficiency(fit_rows, temperature)
    # A sample of healthy readings for the website's scatter chart (the API only reads files).
    points = fit_rows.groupby("plant").sample(n=config.TEMP_WEB_SCATTER_POINTS, random_state=config.RANDOM_SEED)
    points.assign(efficiency_pct=(100 * points["efficiency_norm"]).round(2))[
        ["plant", "module_temp", "efficiency_pct"]].round(2).to_parquet(config.TEMPERATURE_POINTS_FILE, index=False)
    return metrics, temperature


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows terminals and the "—" dash
    result, heat = build_weather()
    for plant, info in result["by_plant"].items():
        print(f"\n{plant}: {info['days']} days, sky by day {info['days_by_dominant_sky']}, "
              f"avg sunshine score {info['avg_sunshine_score']}")
        for kind in ["sunniest_day", "cloudiest_day"]:
            day = info[kind]
            print(f"  {kind:13s} {day['date']}  score {day['sunshine_score']}  CSI {day['avg_csi']}  {day['summary']}")
        print(f"  sanity: {info['sanity']}")
    for plant, info in heat["by_plant"].items():
        print(f"\n{plant} temperature coefficient {info['coefficient_pct_per_c']} %/°C "
              f"(95% range {info['ci95_pct_per_c']}, {info['rows']:,} rows / {info['days']} days); "
              f"no-alert cross-check {info['cross_check_no_alert_rows_pct_per_c']}; "
              f"physics model {info['physics_model_gamma_pct_per_c']}; by sunlight band {info['by_sunlight_band_pct_per_c']}")
        print(f"  heat loss {info['heat_loss_kwh_total']:,.0f} kWh = ₹{info['heat_loss_inr_total']:,.0f} "
              f"({info['heat_loss_pct_of_25c_energy']}% of 25 °C energy); hot hours {info['hot_hours_total']}")
        print(f"  panel heating {info['panel_heating']}")
        print(f"  hottest day {info['hottest_day']['date']}: {info['hottest_day']['summary']}")
