"""Write reports/data_quality.md in plain English from the numbers computed in explore_data.py.

Every number in the report comes from the stats dictionary — nothing is typed in by hand.
"""

from engine import config

COLUMN_GUIDE = [
    ("DATE_TIME", "All files", "When the reading was taken. One reading every 15 minutes."),
    ("PLANT_ID", "All files", "Which solar plant (4135001 = Plant 1, 4136001 = Plant 2)."),
    ("SOURCE_KEY", "Generation", "The ID of one **inverter** — the box that turns the panels' DC "
     "electricity into AC electricity for the grid. ~22 per plant. This is what we monitor."),
    ("SOURCE_KEY", "Weather", "The ID of the plant's single weather sensor (not an inverter)."),
    ("DC_POWER", "Generation", "Power (kW) coming **in** from the solar panels. DC = direct current, "
     "like a battery."),
    ("AC_POWER", "Generation", "Power (kW) going **out** to the grid after the inverter. AC = "
     "alternating current, like a wall socket. Should be a little less than DC (small conversion loss)."),
    ("DAILY_YIELD", "Generation", "Energy (kWh) the inverter has produced **so far today**. Should "
     "start at 0 each morning and only go up during the day."),
    ("TOTAL_YIELD", "Generation", "Energy (kWh) produced over the inverter's **whole life**. Should "
     "only ever go up."),
    ("AMBIENT_TEMPERATURE", "Weather", "Air temperature around the plant (°C)."),
    ("MODULE_TEMPERATURE", "Weather", "Temperature of the solar panels themselves (°C). Hot panels "
     "make a bit less power."),
    ("IRRADIATION", "Weather", "Strength of the sunlight hitting the panels (about kW per m²). "
     "0 at night, around 1 at a sunny noon. More sunlight = more power."),
]


def _files_section(stats):
    """Build the table describing each raw file."""
    lines = ["## 1. The 4 files", "",
             "| File | Rows | Days | Date range | Sources (inverters / sensors) | Blank cells | Duplicate readings |",
             "|---|---|---|---|---|---|---|"]
    for key, info in stats["files"].items():
        lines.append(f"| `{config.RAW_FILES[key].name}` | {info['rows']:,} | {info['days']} | "
                     f"{info['date_start'][:10]} → {info['date_end'][:10]} | "
                     f"{info['unique_source_keys']} | {info['missing_values']} | {info['duplicate_readings']} |")
    lines += ["", "Date formats differ: Plant 1 generation uses `15-05-2020 00:00` (day first), the other "
              "three use `2020-05-15 00:00:00`. We read each file with its exact format "
              "(`DATE_FORMATS` in `engine/config.py`).", ""]
    return lines


def _columns_section():
    """Build the plain-English column dictionary."""
    lines = ["## 2. What every column means", "", "| Column | File | Meaning |", "|---|---|---|"]
    lines += [f"| `{name}` | {where} | {meaning} |" for name, where, meaning in COLUMN_GUIDE]
    return lines + [""]


def _missing_section(stats):
    """Build the section about missing readings per plant."""
    lines = ["## 3. Missing readings", ""]
    for plant_key, p in stats["plants"].items():
        name = plant_key.replace("_", " ").title()
        lines += [f"### {name}",
                  f"- Expected per inverter: {p['days']} days × {config.READINGS_PER_DAY} = "
                  f"**{p['expected_readings_per_inverter']:,}** readings.",
                  f"- Actual per inverter: min {p['actual_readings_per_inverter_min']:,}, "
                  f"median {p['actual_readings_per_inverter_median']:,.0f}, "
                  f"max {p['actual_readings_per_inverter_max']:,}.",
                  f"- In total **{p['total_missing_readings']:,} readings ({p['missing_pct']}%)** are missing.",
                  f"- The weather sensor is missing {p['weather_missing_timestamps']} of its "
                  f"{p['expected_readings_per_inverter']:,} timestamps.",
                  f"- {p['inverters_with_missing_daylight']} of {p['inverters']} inverters miss at least "
                  f"one of the {p['daylight_slots']:,} daylight slots. Worst 5:", "",
                  "| Inverter | Missing daylight readings | % of daylight |", "|---|---|---|"]
        lines += [f"| `{w['inverter']}` | {w['missing_daylight_readings']:,} | {w['missing_daylight_pct']}% |"
                  for w in p["worst_missing_daylight"]]
        lines.append("")
    lines += ["_Note: \"daylight\" is only known for slots where the weather sensor reported. A gap where "
              "the inverter AND the weather sensor are both silent is counted in the total missing, but "
              "not in the daylight columns._", ""]
    return lines


def _issues_section(stats):
    """Build the table of every issue with its size and how we will handle it."""
    p1, p2 = stats["plants"]["plant_1"], stats["plants"]["plant_2"]
    factor = stats["plant_1_dc_inflation_factor_vs_plant_2"]
    rows = [
        ("Plant 1 DC_POWER is about 10× too large",
         f"Median AC÷DC in daylight: Plant 1 = {p1['ac_dc_ratio_median']}, Plant 2 = "
         f"{p2['ac_dc_ratio_median']}. Plant 1 keeps only ~{p1['ac_dc_ratio_median'] * 100:.1f}% of DC, "
         f"which is impossible → Plant 1 DC is ~{factor}× too big. **Quirk confirmed.**",
         "Phase 2: divide Plant 1 DC by a factor computed from the data. Labelled ASSUMPTION."),
        ("Missing inverter readings",
         f"Plant 1: {p1['missing_pct']}% missing. Plant 2: {p2['missing_pct']}% missing; worst inverter "
         f"misses {p2['worst_missing_daylight'][0]['missing_daylight_pct']}% of daylight.",
         "Phase 2: keep gaps as explicit rows (`is_missing = True`), never fill with fake power. "
         "Phase 4: raise a **Data gap / communication loss** alert."),
        ("Missing weather timestamps",
         f"Plant 1: {p1['weather_missing_timestamps']}, Plant 2: {p2['weather_missing_timestamps']}.",
         "Phase 2: no sunlight value → we cannot compute expected power there; mark and skip."),
        ("AC greater than DC",
         f"Plant 1: {p1['ac_greater_than_dc_rows']} rows. Plant 2: {p2['ac_greater_than_dc_rows']} rows, "
         f"at most {p2['ac_greater_than_dc_max_excess_pct']}% above DC.",
         "Tiny measurement noise, not a real fault. Keep the rows; count them in Phase 2."),
        ("Negative power or sunlight",
         f"Power: P1 {p1['negative_dc_or_ac_rows']}, P2 {p2['negative_dc_or_ac_rows']}. "
         f"Irradiation: P1 {p1['negative_irradiation_rows']}, P2 {p2['negative_irradiation_rows']}.",
         "Nothing to fix. Phase 2 tests will keep checking."),
        ("Sunlight at night (20:00–05:00)",
         f"Plant 1: {p1['night_irradiation_rows']} rows. Plant 2: {p2['night_irradiation_rows']} rows, "
         f"max {p2['night_irradiation_max']}.",
         f"Tiny sensor noise, far below our daylight threshold ({stats['daylight_irradiation_threshold']}), "
         "so it is automatically treated as night."),
        ("DAILY_YIELD does not start the day at 0",
         f"Plant 1: {p1['daily_yield_not_zero_at_day_start']} of {p1['inverter_days']} inverter-days. "
         f"Plant 2: {p2['daily_yield_not_zero_at_day_start']} of {p2['inverter_days']}. Of these, "
         f"{p1['daily_yield_not_zero_at_midnight']} (P1) and {p2['daily_yield_not_zero_at_midnight']} (P2) "
         "are the 00:00 reading still showing yesterday's total (the counter resets a bit late).",
         "We do **not** use DAILY_YIELD for energy. We compute energy ourselves: AC_POWER × 0.25 h."),
        ("DAILY_YIELD goes down during the day",
         f"Drops of any kind: P1 {p1['daily_yield_drops_total']}, P2 {p2['daily_yield_drops_total']}. "
         f"Drops while the sun is up: P1 {p1['daily_yield_drops_in_daylight']}, "
         f"P2 {p2['daily_yield_drops_in_daylight']}.",
         "Same as above — the counter is unreliable, so we ignore it for energy."),
        ("TOTAL_YIELD is broken in Plant 2",
         f"Plant 2: {p2['total_yield_zero_rows']} readings are 0 and the counter goes down "
         f"{p2['total_yield_drops']} times; inverter lifetime totals range from "
         f"{p2['total_yield_max_min_inverter']:,.0f} to {p2['total_yield_max_max_inverter']:,.0f} kWh. "
         f"Plant 1: {p1['total_yield_zero_rows']} zeros, {p1['total_yield_drops']} drops (fine).",
         "We do **not** use TOTAL_YIELD. Plant-level counter problems feed the **Sensor/data issue** alert."),
    ]
    lines = ["## 4. Issues found and how we handle them", "",
             "| Issue | Size (measured) | How we handle it |", "|---|---|---|"]
    lines += [f"| {issue} | {size} | {action} |" for issue, size, action in rows]
    return lines + [""]


def write_data_quality_report(stats):
    """Write the full beginner-friendly data-quality report to reports/data_quality.md."""
    lines = ["# Data quality report", "",
             "_Generated by `python -m engine.explore_data` — do not edit by hand; re-run the script._", "",
             "Dataset: Kaggle **\"Solar Power Generation Data\"** by anikannal — two solar plants in India. "
             "Plant location (GPS) is **not** in the dataset.", "",
             f"A 15-minute slot counts as **daylight** when irradiation > "
             f"{stats['daylight_irradiation_threshold']} (`DAYLIGHT_IRRADIATION_THRESHOLD` in config).", ""]
    lines += _files_section(stats) + _columns_section() + _missing_section(stats) + _issues_section(stats)
    config.DATA_QUALITY_REPORT.write_text("\n".join(lines), encoding="utf-8")
