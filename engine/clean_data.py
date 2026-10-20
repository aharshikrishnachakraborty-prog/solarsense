"""Clean and merge the raw data into one tidy table (Phase 2).

Run from the solarsense folder with:   python -m engine.clean_data
Creates data/processed/clean.parquet: one row per inverter per 15 minutes,
INCLUDING missing readings (flagged is_missing = True, power left blank).
"""

import pandas as pd

from engine import config
from engine.assumptions import record_assumption
from engine.load_data import load_generation, load_weather
from engine.metrics import save_metrics_section


def daylight_ac_dc_ratio(generation, weather):
    """Median AC ÷ DC during daylight — a healthy inverter keeps ~95–99% of its DC power."""
    merged = generation.merge(weather[["DATE_TIME", "IRRADIATION"]], on="DATE_TIME")
    daylight = merged[(merged["IRRADIATION"] > config.DAYLIGHT_IRRADIATION_THRESHOLD)
                      & (merged["DC_POWER"] > 0)]
    return float((daylight["AC_POWER"] / daylight["DC_POWER"]).median())


def compute_dc_scale_factor(raw):
    """How many times too big the suspect plant's DC is, measured against the reference plant."""
    suspect_ratio = daylight_ac_dc_ratio(*raw[config.DC_SUSPECT_PLANT])
    reference_ratio = daylight_ac_dc_ratio(*raw[config.DC_REFERENCE_PLANT])
    # If both plants converted DC to AC equally well, their ratios would match.
    # So the suspect's DC must be divided by (reference ratio ÷ suspect ratio).
    return round(reference_ratio / suspect_ratio, 3), suspect_ratio, reference_ratio


def build_full_grid(generation, plant):
    """Make one row for EVERY inverter at EVERY 15-minute time, so gaps become visible rows."""
    first_day = generation["DATE_TIME"].min().normalize()
    last_slot = generation["DATE_TIME"].max().normalize() + pd.Timedelta(hours=23, minutes=45)
    times = pd.date_range(first_day, last_slot, freq="15min")
    inverters = sorted(generation["SOURCE_KEY"].unique())
    grid = pd.MultiIndex.from_product([inverters, times], names=["inverter", "timestamp"]).to_frame(index=False)
    grid["plant"] = plant
    return grid


def clean_plant(plant, generation, weather, dc_scale):
    """Turn one plant's raw generation + weather into the clean table."""
    grid = build_full_grid(generation, plant)

    readings = generation.rename(columns={
        "SOURCE_KEY": "inverter", "DATE_TIME": "timestamp", "DC_POWER": "dc_kw", "AC_POWER": "ac_kw"})
    readings = readings[["inverter", "timestamp", "dc_kw", "ac_kw"]]
    readings["dc_kw"] = readings["dc_kw"] / dc_scale   # dc_scale is 1.0 for a normal plant
    table = grid.merge(readings, on=["inverter", "timestamp"], how="left")
    # A grid slot with no matching reading = the inverter did not report. We leave
    # its power blank (NaN) — never fill it with an invented number.
    table["is_missing"] = table["ac_kw"].isna()

    sensor = weather.rename(columns={
        "DATE_TIME": "timestamp", "IRRADIATION": "irradiation",
        "MODULE_TEMPERATURE": "module_temp", "AMBIENT_TEMPERATURE": "ambient_temp"})
    table = table.merge(sensor[["timestamp", "irradiation", "module_temp", "ambient_temp"]],
                        on="timestamp", how="left")
    table["weather_missing"] = table["irradiation"].isna()

    table["date"] = table["timestamp"].dt.date.astype(str)
    table["hour"] = table["timestamp"].dt.hour
    # Without a sunlight reading we cannot say it was daylight, so it counts as False.
    table["is_daylight"] = table["irradiation"].fillna(0) > config.DAYLIGHT_IRRADIATION_THRESHOLD
    return table


def flag_impossible_values(table):
    """Blank out physically impossible values and count them (returned as a dictionary)."""
    negative_power = (table["dc_kw"] < 0) | (table["ac_kw"] < 0)
    table.loc[negative_power, ["dc_kw", "ac_kw"]] = float("nan")
    table.loc[negative_power, "is_missing"] = True   # treated like a missing reading

    # AC slightly above DC is measurement noise (both are 15-minute averages);
    # we keep the values but flag them so they can be inspected.
    table["ac_above_dc"] = table["ac_kw"] > table["dc_kw"]

    negative_sun = table["irradiation"] < 0
    table.loc[negative_sun, "irradiation"] = 0.0
    return {
        "negative_power_rows_blanked": int(negative_power.sum()),
        "ac_above_dc_rows_flagged": int(table["ac_above_dc"].sum()),
        "negative_irradiation_rows_set_to_zero": int(negative_sun.sum()),
    }


COLUMN_ORDER = ["plant", "inverter", "timestamp", "date", "hour", "is_daylight", "is_missing",
                "weather_missing", "dc_kw", "ac_kw", "irradiation", "module_temp", "ambient_temp",
                "ac_above_dc"]


def clean_all():
    """Clean both plants, save clean.parquet, record stats and the DC assumption."""
    raw = {plant: (load_generation(plant), load_weather(plant)) for plant in config.PLANTS}
    dc_scale, suspect_ratio, reference_ratio = compute_dc_scale_factor(raw)

    tables, stats = [], {"plants": {}}
    for plant in config.PLANTS:
        generation, weather = raw[plant]
        scale = dc_scale if plant == config.DC_SUSPECT_PLANT else 1.0
        table = clean_plant(plant, generation, weather, scale)
        plant_stats = flag_impossible_values(table)
        plant_stats.update({
            "rows": int(len(table)),
            "inverters": int(table["inverter"].nunique()),
            "raw_readings": int(len(generation)),
            "missing_rows": int(table["is_missing"].sum()),
            "missing_daylight_rows": int((table["is_missing"] & table["is_daylight"]).sum()),
            "weather_missing_rows": int(table["weather_missing"].sum()),
            "daylight_rows": int(table["is_daylight"].sum()),
            "dc_scale_applied": scale,
            "ac_dc_ratio_after_fix": round(float(
                (table["ac_kw"] / table["dc_kw"])[table["is_daylight"] & (table["dc_kw"] > 0)].median()), 4),
        })
        stats["plants"][f"plant_{plant}"] = plant_stats
        tables.append(table)

    clean = pd.concat(tables, ignore_index=True)[COLUMN_ORDER]
    clean.to_parquet(config.CLEAN_FILE, index=False)

    stats["dc_scale_factor"] = dc_scale
    stats["total_rows"] = int(len(clean))
    save_metrics_section("cleaning", stats)
    record_assumption(
        key="plant_1_dc_scale_factor",
        title=f"Plant {config.DC_SUSPECT_PLANT} DC_POWER divided by a scale factor",
        value=dc_scale, unit="×",
        why=(f"In daylight Plant {config.DC_SUSPECT_PLANT} AC÷DC was {suspect_ratio:.4f} (physically "
             f"impossible) vs {reference_ratio:.4f} for Plant {config.DC_REFERENCE_PLANT}. We assume the "
             f"inverters are similar and the DC sensor/logging was ~{dc_scale}× too large."),
        source="Computed from the data (engine/clean_data.py)")
    return clean, stats


if __name__ == "__main__":
    clean_table, cleaning_stats = clean_all()
    print(f"Saved {config.CLEAN_FILE} with {cleaning_stats['total_rows']:,} rows.")
    print(f"Plant {config.DC_SUSPECT_PLANT} DC divided by {cleaning_stats['dc_scale_factor']}")
    for name, info in cleaning_stats["plants"].items():
        print(f"{name}: {info['rows']:,} rows = {info['inverters']} inverters x "
              f"{info['rows'] // info['inverters']} slots | missing {info['missing_rows']:,} "
              f"(daylight {info['missing_daylight_rows']:,}) | AC/DC after fix {info['ac_dc_ratio_after_fix']}")
