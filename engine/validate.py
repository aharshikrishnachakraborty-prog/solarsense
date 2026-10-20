"""Prove the detector works with injected faults — our evidence without official labels (Phase 7).

Run from the solarsense folder with:   python -m engine.validate
1. Take healthy (no alert) inverter-days from the TEST period.
2. Break them on purpose: trip, underperformance, data gap, soiling (seeded, reproducible).
3. Run the SAME detector with the SAME thresholds and count caught / missed / false alarms.
4. Repeat with sensitive and strict thresholds to show the trade-off.
"""

from collections import Counter

import numpy as np
import pandas as pd

from engine import config
from engine.fault_injection import (TARGET_TYPE, false_alarms_on_clean_days, inject_one, inject_soiling,
                                    load_test_data, pick_days, run_detector, score_run, thresholds)
from engine.metrics import save_metrics_section
from engine.validate_report import make_example_chart

SIZE_BUCKETS = config.VALIDATION_SIZE_BUCKETS   # how "big" each fault was: easy vs hard to catch


def injection_runs(test, clean_days, faults, n_runs):
    """Inject each fault type n_runs times, detect, and return scored injections + false alarms."""
    rng = np.random.default_rng(config.RANDOM_SEED)
    records, false_alarms, example = [], Counter(), None
    for fault in faults:
        for run in range(n_runs):
            table = test.copy()
            if fault == "soiling":
                # Soiling needs an inverter healthy on EVERY test day; 2 per run keeps the peer median fair.
                days = table["date"].nunique()
                per_inverter = Counter((p, i) for p, i, _ in clean_days)
                eligible = sorted(k for k, n in per_inverter.items() if n == days)
                chosen = [eligible[k] for k in rng.choice(len(eligible), size=2, replace=False)]
                injections = [inject_soiling(table, plant, inverter, rng) for plant, inverter in chosen]
            else:
                injections = [inject_one(table, fault, *pick, rng) for pick in pick_days(clean_days, rng)]
            events = run_detector(table)
            scored, unmatched = score_run(injections, events)
            # Only count false alarms of the type this run is testing (fair per-type precision).
            target = TARGET_TYPE[fault]
            false_alarms[target] += false_alarms_on_clean_days(unmatched, clean_days).get(target, 0)
            for record in scored:
                record["run"] = run
            records += scored
            if example is None and fault == "underperformance":
                example = next(({"record": r, "injected": table, "events": events} for r in scored
                                if r["caught"] and r["plant"] == 1), None)
    return pd.DataFrame(records), dict(false_alarms), example


def summarise(records, false_alarms, clean_day_count):
    """Recall, precision, delay and loss-estimate error per fault type, plus recall by fault size."""
    summary = {}
    for fault, group in records.groupby("fault"):
        target = TARGET_TYPE[fault]
        caught = int(group["caught"].sum())
        fp = int(false_alarms.get(target, 0))
        error_pct = 100 * (group["estimated_kwh"] - group["true_kwh"]) / group["true_kwh"]
        unit, edges = SIZE_BUCKETS[fault]
        buckets = pd.cut(group["size"], edges, right=False)
        summary[fault] = {
            "detected_as": target, "injections": int(len(group)), "caught": caught,
            "caught_as_other_type": int(group["caught_as_other_type"].sum()),
            "missed": int(len(group) - caught - group["caught_as_other_type"].sum()),
            "recall_pct": round(100 * caught / len(group), 1),
            "false_alarms": fp, "precision_pct": round(100 * caught / max(caught + fp, 1), 1),
            "false_alarms_per_100_clean_days": round(100 * fp / clean_day_count, 2),
            "avg_delay_minutes": None if group["delay_minutes"].isna().all() else round(float(group["delay_minutes"].mean()), 1),
            "loss_error_median_abs_pct": None if error_pct.isna().all() else round(float(error_pct.abs().median()), 1),
            "loss_error_mean_pct": None if error_pct.isna().all() else round(float(error_pct.mean()), 1),
            "recall_by_plant_pct": {f"plant_{p}": round(100 * float(g["caught"].mean()), 1)
                                    for p, g in group.groupby("plant")},
            "size_unit": unit,
            "recall_by_size_pct": {str(b): {"injections": int(len(g)), "recall_pct": round(100 * float(g["caught"].mean()), 1)}
                                   for b, g in group.groupby(buckets, observed=True)},
        }
    return summary


def threshold_tradeoff(test, clean_days):
    """Same injections under 3 threshold settings: more sensitive = more caught AND more false alarms."""
    rows = []
    for name, overrides in config.VALIDATION_THRESHOLD_SETTINGS.items():
        with thresholds(**overrides):
            records, _, _ = injection_runs(test, clean_days, ["trip", "underperformance"], config.VALIDATION_RUNS)
            baseline = run_detector(test)   # untouched data: every alert on a clean day is a false alarm
            extra = false_alarms_on_clean_days(baseline, clean_days)
        for fault, group in records.groupby("fault"):
            rows.append({"setting": name, "fault": fault, "recall_pct": round(100 * float(group["caught"].mean()), 1),
                         "false_alarms_on_clean_days": int(extra.get(TARGET_TYPE[fault], 0)),
                         "false_alarms_per_100_clean_days": round(100 * extra.get(TARGET_TYPE[fault], 0) / len(clean_days), 2)})
    return pd.DataFrame(rows)


def validate():
    """Run the full validation and save every output."""
    test, clean_days = load_test_data()
    records, false_alarms, example = injection_runs(
        test, clean_days, ["trip", "underperformance", "data_gap"], config.VALIDATION_RUNS)
    soiling, soiling_false, _ = injection_runs(test, clean_days, ["soiling"], config.VALIDATION_SOILING_RUNS)
    records = pd.concat([records, soiling], ignore_index=True)
    false_alarms = Counter(false_alarms) + Counter(soiling_false)

    tradeoff = threshold_tradeoff(test, clean_days)
    records.to_parquet(config.VALIDATION_INJECTIONS_FILE, index=False)
    tradeoff.to_parquet(config.VALIDATION_TRADEOFF_FILE, index=False)

    results = {
        "method": "Faults injected into healthy test-day data (clean inverter-days), detected with the same "
                  "detector and thresholds.",
        "test_dates": [test["date"].min(), test["date"].max()],
        "clean_inverter_days": len(clean_days),
        "caveat": "Healthy days were chosen as days where the default detector raised no alert, so false alarms "
                  "at default thresholds are optimistic (near 0 by construction). The real false-alarm rate "
                  "cannot be measured without labelled faults.",
        "soiling_note": "Soiling is tested on Plant 1 only (the only plant with inverters healthy on every test "
                        "day) and on a 10-day window. Its false alarms are Plant 2 inverters whose output trends "
                        "down within those 10 days; on the full 34 days the same rule raised no degradation alert.",
        "fault_sizes": config.VALIDATION_FAULT_SIZES,   # so the website can label size groups correctly
        "by_fault": summarise(records, false_alarms, len(clean_days)),
        "threshold_tradeoff": tradeoff.to_dict(orient="records"),
    }
    results["example_chart"] = make_example_chart(example, test)
    save_metrics_section("validation", results)
    return results


if __name__ == "__main__":
    output = validate()
    for fault, s in output["by_fault"].items():
        print(f"{fault:17s} injected {s['injections']:3d} | caught {s['caught']:3d} ({s['recall_pct']}%) | "
              f"other type {s['caught_as_other_type']} | missed {s['missed']} | false alarms {s['false_alarms']} | "
              f"precision {s['precision_pct']}% | delay {s['avg_delay_minutes']} min | "
              f"loss error median {s['loss_error_median_abs_pct']}% (mean {s['loss_error_mean_pct']}%)")
        print(f"   by plant {s['recall_by_plant_pct']} | by size ({s['size_unit']}): "
              + ", ".join(f"{b}: {v['recall_pct']}% of {v['injections']}" for b, v in s["recall_by_size_pct"].items()))
    print(pd.DataFrame(output["threshold_tradeoff"]).to_string(index=False))
