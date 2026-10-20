"""Explore the raw data and measure its quality (Phase 1).

Run from the solarsense folder with:   python -m engine.explore_data
It prints a summary, saves numbers under "data" in reports/metrics.json
and writes reports/data_quality.md. It never changes the raw files.
"""

from engine import config
from engine.load_data import load_all
from engine.metrics import save_metrics_section
from engine.report_data_quality import write_data_quality_report


def summarise_file(table):
    """Basic facts about one raw file: size, columns, dates, sources, blanks."""
    return {
        "rows": int(len(table)),
        "columns": list(table.columns),
        "date_start": str(table["DATE_TIME"].min()),
        "date_end": str(table["DATE_TIME"].max()),
        "days": int(table["DATE_TIME"].dt.date.nunique()),
        "unique_source_keys": int(table["SOURCE_KEY"].nunique()),
        "missing_values": int(table.isna().sum().sum()),
        "duplicate_readings": int(table.duplicated(["DATE_TIME", "SOURCE_KEY"]).sum()),
    }


def check_missing_readings(generation, weather):
    """Count how many 15-minute readings each inverter is missing, overall and in daylight."""
    n_days = generation["DATE_TIME"].dt.date.nunique()
    expected_per_inverter = n_days * config.READINGS_PER_DAY
    readings = generation.groupby("SOURCE_KEY").size()

    # Daylight slots = times when the plant's weather sensor saw real sunlight.
    daylight_times = set(
        weather.loc[weather["IRRADIATION"] > config.DAYLIGHT_IRRADIATION_THRESHOLD, "DATE_TIME"]
    )
    missing_daylight = {}
    for inverter, rows in generation.groupby("SOURCE_KEY"):
        missing_daylight[inverter] = len(daylight_times - set(rows["DATE_TIME"]))
    worst = sorted(missing_daylight.items(), key=lambda item: item[1], reverse=True)[:5]

    total_missing = int(expected_per_inverter * len(readings) - readings.sum())
    return {
        "inverters": int(len(readings)),
        "days": int(n_days),
        "expected_readings_per_inverter": int(expected_per_inverter),
        "actual_readings_per_inverter_min": int(readings.min()),
        "actual_readings_per_inverter_median": float(readings.median()),
        "actual_readings_per_inverter_max": int(readings.max()),
        "total_missing_readings": total_missing,
        "missing_pct": round(100 * total_missing / (expected_per_inverter * len(readings)), 2),
        "weather_missing_timestamps": int(expected_per_inverter - weather["DATE_TIME"].nunique()),
        "daylight_slots": len(daylight_times),
        "inverters_with_missing_daylight": int(sum(1 for n in missing_daylight.values() if n > 0)),
        "worst_missing_daylight": [
            {"inverter": inverter, "missing_daylight_readings": int(count),
             "missing_daylight_pct": round(100 * count / len(daylight_times), 1)}
            for inverter, count in worst
        ],
    }


def check_dc_ac_ratio(generation, weather):
    """Measure AC power ÷ DC power in daylight (a real inverter keeps ~95–99% of DC)."""
    merged = generation.merge(weather[["DATE_TIME", "IRRADIATION"]], on="DATE_TIME", how="left")
    daylight = merged[(merged["IRRADIATION"] > config.DAYLIGHT_IRRADIATION_THRESHOLD)
                      & (merged["DC_POWER"] > 0)]
    ratio = daylight["AC_POWER"] / daylight["DC_POWER"]
    return {
        "dc_ac_daylight_rows": int(len(daylight)),
        "ac_dc_ratio_median": round(float(ratio.median()), 4),
        "ac_dc_ratio_p5": round(float(ratio.quantile(0.05)), 4),
        "ac_dc_ratio_p95": round(float(ratio.quantile(0.95)), 4),
    }


def check_impossible_values(generation, weather):
    """Count values that cannot be physically true or that break the counters' rules."""
    gen = generation.sort_values(["SOURCE_KEY", "DATE_TIME"]).copy()
    gen["date"] = gen["DATE_TIME"].dt.date

    ac_above_dc = gen[gen["AC_POWER"] > gen["DC_POWER"]]
    excess_pct = 100 * (ac_above_dc["AC_POWER"] - ac_above_dc["DC_POWER"]) / ac_above_dc["DC_POWER"]

    is_night = weather["DATE_TIME"].dt.hour.isin(config.NIGHT_HOURS)
    night_sun = weather[is_night & (weather["IRRADIATION"] > 0)]

    # DAILY_YIELD should start each day at 0 and only go up during the day.
    first_of_day = gen.groupby(["SOURCE_KEY", "date"]).first()
    yield_change = gen.groupby(["SOURCE_KEY", "date"])["DAILY_YIELD"].diff()
    drops = gen[yield_change < 0]
    daylight_times = set(
        weather.loc[weather["IRRADIATION"] > config.DAYLIGHT_IRRADIATION_THRESHOLD, "DATE_TIME"]
    )
    daytime_drops = drops[drops["DATE_TIME"].isin(daylight_times)]

    # TOTAL_YIELD is a lifetime counter: it should never be 0 or go down.
    total_change = gen.groupby("SOURCE_KEY")["TOTAL_YIELD"].diff()
    return {
        "negative_dc_or_ac_rows": int(((gen["DC_POWER"] < 0) | (gen["AC_POWER"] < 0)).sum()),
        "negative_irradiation_rows": int((weather["IRRADIATION"] < 0).sum()),
        "ac_greater_than_dc_rows": int(len(ac_above_dc)),
        "ac_greater_than_dc_max_excess_pct": round(float(excess_pct.max()), 2) if len(ac_above_dc) else 0.0,
        "night_irradiation_rows": int(len(night_sun)),
        "night_irradiation_max": round(float(night_sun["IRRADIATION"].max()), 4) if len(night_sun) else 0.0,
        "daily_yield_not_zero_at_day_start": int((first_of_day["DAILY_YIELD"] > 0).sum()),
        # Of those, how many are the 00:00 reading (counter simply resets a bit late).
        "daily_yield_not_zero_at_midnight": int(
            ((first_of_day["DAILY_YIELD"] > 0) & (first_of_day["DATE_TIME"].dt.hour == 0)).sum()
        ),
        "inverter_days": int(len(first_of_day)),
        "daily_yield_drops_total": int(len(drops)),
        "daily_yield_drops_in_daylight": int(len(daytime_drops)),
        "total_yield_zero_rows": int((gen["TOTAL_YIELD"] == 0).sum()),
        "total_yield_drops": int((total_change < 0).sum()),
        "total_yield_max_min_inverter": float(gen.groupby("SOURCE_KEY")["TOTAL_YIELD"].max().min()),
        "total_yield_max_max_inverter": float(gen.groupby("SOURCE_KEY")["TOTAL_YIELD"].max().max()),
    }


def explore():
    """Run every check on both plants, save the numbers and write the report."""
    tables = load_all()
    stats = {"files": {}, "plants": {}}
    for file_key, table in tables.items():
        stats["files"][file_key] = summarise_file(table)

    for plant in config.PLANTS:
        generation = tables[f"plant_{plant}_generation"]
        weather = tables[f"plant_{plant}_weather"]
        plant_stats = {}
        plant_stats.update(check_missing_readings(generation, weather))
        plant_stats.update(check_dc_ac_ratio(generation, weather))
        plant_stats.update(check_impossible_values(generation, weather))
        stats["plants"][f"plant_{plant}"] = plant_stats

    # How many times too big Plant 1's DC is, using Plant 2 as the "normal" reference.
    stats["plant_1_dc_inflation_factor_vs_plant_2"] = round(
        stats["plants"]["plant_2"]["ac_dc_ratio_median"]
        / stats["plants"]["plant_1"]["ac_dc_ratio_median"], 2
    )
    stats["daylight_irradiation_threshold"] = config.DAYLIGHT_IRRADIATION_THRESHOLD

    save_metrics_section("data", stats)
    write_data_quality_report(stats)
    return stats


def print_summary(stats):
    """Print the most important numbers to the terminal."""
    for file_key, info in stats["files"].items():
        print(f"{file_key}: {info['rows']} rows, {info['days']} days "
              f"({info['date_start']} -> {info['date_end']}), "
              f"{info['unique_source_keys']} source(s), {info['missing_values']} blank cells")
    for plant_key, info in stats["plants"].items():
        print(f"\n{plant_key}: {info['inverters']} inverters, {info['missing_pct']}% readings missing, "
              f"AC/DC median {info['ac_dc_ratio_median']}")
        for row in info["worst_missing_daylight"]:
            print(f"   {row['inverter']}: {row['missing_daylight_readings']} daylight readings missing "
                  f"({row['missing_daylight_pct']}%)")
    print(f"\nPlant 1 DC looks {stats['plant_1_dc_inflation_factor_vs_plant_2']}x too large.")
    print(f"Saved: {config.METRICS_FILE} and {config.DATA_QUALITY_REPORT}")


if __name__ == "__main__":
    print_summary(explore())
