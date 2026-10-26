"""Does knowing the weather make fault detection better? A fair before/after test (Phase W4).

Run from the solarsense folder with:   python -m engine.validate_weather     (~1–2 minutes)
"before" = detector WITHOUT the weather-aware rule, "after" = WITH it (WEATHER_AWARE_UNDER in config.py).
Both versions get exactly the same injected faults (same seed), so any difference comes from the rule:
  1. Injected underperformance on any clean test day (does the rule lose real faults?)
  2. Injected trips + underperformance on CLOUDY clean test days (the hard case: a fault hidden by clouds)
  3. False alarms: underperformance alerts on untouched clean days (all, and cloudy ones)
  4. Underperformance alerts on the real data (whole period) — we cannot say which are real, only how many
At our default thresholds and at the "sensitive" thresholds, where clouds cause many more short alerts.
The rule only touches underperformance; trips, data gaps and soiling use identical rules in both versions.
Decision (printed and saved): keep the rule only if false alarms drop and no injected fault is lost.
"""

import pandas as pd

from engine import config
from engine.fault_injection import false_alarms_on_clean_days, load_test_data, run_detector, thresholds
from engine.metrics import save_metrics_section
from engine.validate import injection_runs

VERSIONS = {"before": False, "after": True}   # WEATHER_AWARE_UNDER off / on
SETTINGS = ["default", "sensitive"]
MODEL_CARD_MARKER = "## Weather-aware fault detection (Phase W4)"


def cloudy_clean_days(clean_days):
    """Clean inverter-days on days whose sunshine score (Phase W1) marks them as cloudy."""
    daily = pd.read_parquet(config.WEATHER_DAILY_FILE)
    cloudy = daily[daily["sunshine_score"] < config.VALIDATION_CLOUDY_DAY_MAX_SUNSHINE]
    cloudy = set(zip(cloudy["plant"], cloudy["date"]))
    return {(plant, inverter, date) for plant, inverter, date in clean_days if (plant, date) in cloudy}


def caught(records, fault):
    """(caught, injected) for one fault type in a set of injection records."""
    group = records[records["fault"] == fault]
    return int(group["caught"].sum()), int(len(group))


def run_version(test, full, clean, cloudy, setting, weather_aware):
    """Every measurement for one threshold setting and one version of the detector."""
    overrides = {**config.VALIDATION_THRESHOLD_SETTINGS[setting], "WEATHER_AWARE_UNDER": weather_aware}
    with thresholds(**overrides):
        any_day, _, _ = injection_runs(test, clean, ["underperformance"], config.VALIDATION_RUNS)
        on_cloudy, _, _ = injection_runs(test, cloudy, ["trip", "underperformance"], config.VALIDATION_RUNS)
        untouched = run_detector(test)     # nothing injected: every alert on a clean day is a false alarm
        real = run_detector(full)          # the real data, whole period
    row = {"setting": setting, "version": "after" if weather_aware else "before"}
    for name, (hit, total) in {"under_any_day": caught(any_day, "underperformance"),
                               "under_cloudy_day": caught(on_cloudy, "underperformance"),
                               "trip_cloudy_day": caught(on_cloudy, "trip")}.items():
        row[f"{name}_caught"], row[f"{name}_injected"] = hit, total
        row[f"{name}_recall_pct"] = round(100 * hit / total, 1) if total else None
    row["false_alarms_clean_days"] = int(false_alarms_on_clean_days(untouched, clean).get("UNDERPERFORMANCE", 0))
    row["false_alarms_cloudy_days"] = int(false_alarms_on_clean_days(untouched, cloudy).get("UNDERPERFORMANCE", 0))
    row["real_underperformance_alerts"] = int((real["fault_type"] == "UNDERPERFORMANCE").sum()) if len(real) else 0
    return row


def decide(table):
    """Keep the rule only if no injected fault is lost (any setting) and false alarms drop overall."""
    before = table[table["version"] == "before"].set_index("setting")
    after = table[table["version"] == "after"].set_index("setting")
    caught_columns = [c for c in table.columns if c.endswith("_caught")]
    lost = int((before[caught_columns] - after[caught_columns]).clip(lower=0).to_numpy().sum())
    false_before = int(before["false_alarms_clean_days"].sum())
    false_after = int(after["false_alarms_clean_days"].sum())
    keep = lost == 0 and false_after < false_before
    return {"keep_rule": keep, "injected_faults_lost": lost,
            "false_alarms_before": false_before, "false_alarms_after": false_after,
            "rule_enabled_in_config": config.WEATHER_AWARE_UNDER,
            "verdict": (f"{'KEEP' if keep else 'DO NOT KEEP'} the weather-aware rule: false alarms on clean test "
                        f"days {false_before} → {false_after} (default + sensitive thresholds), injected faults "
                        f"lost: {lost}.")}


def validate_weather():
    """Run both versions at both settings, save the table and the "validation_weather" metrics."""
    test, clean = load_test_data()
    cloudy = cloudy_clean_days(clean)
    full = pd.read_parquet(config.EXPECTED_FILE)
    rows = [run_version(test, full, clean, cloudy, setting, aware)
            for setting in SETTINGS for aware in VERSIONS.values()]
    table = pd.DataFrame(rows)
    table.to_parquet(config.VALIDATION_WEATHER_FILE, index=False)
    result = {"method": __doc__.split("\n\n")[0].split("\n")[0].strip() + " Same seeded injections in both versions.",
              "rule": (f"Under a difficult sky (Overcast, or variability ≥ {config.SKY_HIGH_VARIABILITY}) for at least "
                       f"{config.UNDER_DIFFICULT_SKY_SHARE:.0%} of its readings, an underperformance event must last ≥ "
                       f"{config.UNDER_DIFFICULT_MIN_INTERVALS * config.INTERVAL_HOURS:g} h OR be at least "
                       f"{1 - config.UNDER_STRONG_PEER_RATIO:.0%} below its neighbours."),
              "cloudy_day_definition": f"sunshine score below {config.VALIDATION_CLOUDY_DAY_MAX_SUNSHINE} (Phase W1)",
              "clean_inverter_days": len(clean), "cloudy_clean_inverter_days": len(cloudy),
              "caveat": ("Clean days are days with no alert at default thresholds, so false alarms at default are ~0 "
                         "by construction; the sensitive setting shows how the rule behaves when clouds DO cause "
                         "alerts. Without official fault labels we cannot tell which real alerts are false."),
              "results": rows, **decide(table)}
    save_metrics_section("validation_weather", result)
    update_model_card(result)
    return result


def update_model_card(result):
    """Replace the weather section at the end of reports/model_card.md (the rest is written by Phase 3)."""
    card = config.MODEL_CARD.read_text(encoding="utf-8") if config.MODEL_CARD.exists() else ""
    card = card.split(MODEL_CARD_MARKER)[0].rstrip() + "\n\n"
    rows = ["| Thresholds | Version | Underperf. caught (any day) | Underperf. caught (cloudy days) | "
            "Trips caught (cloudy days) | False alarms (clean days) | Real underperf. alerts |", "|---|---|---|---|---|---|---|"]
    for r in result["results"]:
        rows.append(f"| {r['setting']} | {r['version']} | {r['under_any_day_caught']}/{r['under_any_day_injected']} | "
                    f"{r['under_cloudy_day_caught']}/{r['under_cloudy_day_injected']} | "
                    f"{r['trip_cloudy_day_caught']}/{r['trip_cloudy_day_injected']} | {r['false_alarms_clean_days']} | "
                    f"{r['real_underperformance_alerts']} |")
    section = [MODEL_CARD_MARKER, "",
               "Generated by `python -m engine.validate_weather` — do not edit by hand.", "",
               "**What every alert now carries:** the sky during the alert (Clear / Partly cloudy / Cloudy / Overcast, "
               "read from the sunlight — Phase W1), its clear-sky index, the panel temperature, a confidence level "
               "(High / Medium / Low) and a weather sentence, e.g. \"Sky was clear (clear-sky index 0.98), so low "
               "output is NOT caused by clouds\". These never change WHICH alerts are raised.", "",
               f"**Rule we tested:** {result['rule']}", "",
               f"**Before/after test** (same seeded faults in both versions; cloudy day = "
               f"{result['cloudy_day_definition']}):", "", *rows, "",
               f"**Decision:** {result['verdict']} The rule is "
               f"{'ON' if result['rule_enabled_in_config'] else 'OFF'} in engine/config.py (WEATHER_AWARE_UNDER).", "",
               f"**Caveat:** {result['caveat']}", ""]
    config.MODEL_CARD.write_text(card + "\n".join(section), encoding="utf-8")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    output = validate_weather()
    print(f"Clean inverter-days: {output['clean_inverter_days']} (cloudy: {output['cloudy_clean_inverter_days']})")
    print(pd.DataFrame(output["results"]).to_string(index=False))
    print(output["verdict"], f"(rule enabled in config: {output['rule_enabled_in_config']})")
