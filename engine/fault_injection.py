"""Building blocks for the injected-fault test: break data on purpose, then score the detector.

Used by engine/validate.py. We have no official fault labels, so we make our own:
break healthy data with a known start, end and size, run the SAME detector, compare.
"""

from contextlib import contextmanager

import numpy as np
import pandas as pd

from engine import config
from engine.detect_faults import add_interval_flags, detect_inverter_events
from engine.expected_model import add_residuals

INTERVAL = pd.Timedelta(minutes=15)
# Which alert type SHOULD catch each injected fault.
TARGET_TYPE = {"trip": "INVERTER_TRIP", "underperformance": "UNDERPERFORMANCE",
               "soiling": "DEGRADATION", "data_gap": "DATA_GAP"}
MIN_INTERVALS_SETTING = {"INVERTER_TRIP": "TRIP_MIN_INTERVALS", "UNDERPERFORMANCE": "UNDER_MIN_INTERVALS",
                         "DATA_GAP": "GAP_MIN_INTERVALS"}


@contextmanager
def thresholds(**overrides):
    """Temporarily change detector thresholds (config.py on disk is never changed)."""
    original = {name: getattr(config, name) for name in overrides}
    for name, value in overrides.items():
        setattr(config, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(config, name, value)


def load_test_data():
    """Test-day rows, plus the set of clean (no alert) inverter-days that we may break."""
    table = pd.read_parquet(config.EXPECTED_FILE)
    test = table[table["split"] == "test"].reset_index(drop=True)
    alerts = pd.read_parquet(config.ALERTS_FILE)
    alerts = alerts[alerts["inverter"] != "ALL"]
    busy = set()
    for alert in alerts.itertuples():
        for day in pd.date_range(alert.start.normalize(), (alert.end - pd.Timedelta(minutes=1)).normalize()):
            busy.add((alert.plant, alert.inverter, str(day.date())))
    all_days = set(test[["plant", "inverter", "date"]].itertuples(index=False, name=None))
    return test, all_days - busy


def run_detector(table):
    """Recompute residuals/peers on the (possibly injected) data and run the real detector."""
    flagged = add_interval_flags(add_residuals(table.copy()))
    return pd.DataFrame(detect_inverter_events(flagged))


def _quarter_hours(limits):
    """All durations from smallest to largest in 15-minute steps, e.g. (1, 4) -> 1.0, 1.25 … 4.0."""
    return np.arange(limits[0], limits[1] + 0.25, 0.25)


def inject_one(table, fault, plant, inverter, date, rng):
    """Break one inverter-day in place; return a record of exactly what we did."""
    day = (table["plant"] == plant) & (table["inverter"] == inverter) & (table["date"] == date)
    times = table.loc[day, "timestamp"].sort_values()
    sizes = config.VALIDATION_FAULT_SIZES
    if fault == "trip":
        hours = rng.choice(_quarter_hours(sizes["trip_hours"]))
        centre = (pd.Timestamp(date) + pd.Timedelta(hours=sizes["trip_centre_hour"])
                  + pd.Timedelta(minutes=15 * int(rng.integers(-4, 5))))
        start = centre - pd.Timedelta(hours=hours / 2)
        size = hours
    else:
        hours = rng.choice(_quarter_hours(sizes[f"{fault}_hours"]))
        first_hour, last_hour = sizes["window_hours"]
        latest = pd.Timestamp(date) + pd.Timedelta(hours=last_hour) - pd.Timedelta(hours=hours)
        slots = times[(times >= pd.Timestamp(date) + pd.Timedelta(hours=first_hour)) & (times <= latest)]
        start = slots.iloc[int(rng.integers(len(slots)))]
        size = rng.uniform(*sizes["underperformance_output_kept"]) if fault == "underperformance" else hours
    start = start.floor("15min")
    end = start + pd.Timedelta(hours=hours)
    window = day & (table["timestamp"] >= start) & (table["timestamp"] < end)
    original = table.loc[window, "ac_kw"]

    if fault == "trip":
        true_kwh = original.sum() * config.INTERVAL_HOURS
        table.loc[window, "ac_kw"] = 0.0
    elif fault == "underperformance":
        true_kwh = (original * (1 - size)).sum() * config.INTERVAL_HOURS
        table.loc[window, "ac_kw"] = original * size
    else:   # data gap: the readings disappear
        true_kwh = original.sum() * config.INTERVAL_HOURS
        table.loc[window, ["ac_kw", "dc_kw"]] = np.nan
        table.loc[window, "is_missing"] = True
    return {"fault": fault, "plant": plant, "inverter": inverter, "start": start, "end": end,
            "size": round(float(size), 3), "true_kwh": round(float(true_kwh), 1)}


def inject_soiling(table, plant, inverter, rng):
    """Gradual decline (a few tenths of a % per day) over all test days for one inverter."""
    rate = rng.uniform(*config.VALIDATION_FAULT_SIZES["soiling_pct_per_day"])
    rows = (table["plant"] == plant) & (table["inverter"] == inverter)
    first = pd.Timestamp(table["date"].min())
    day_number = (pd.to_datetime(table.loc[rows, "date"]) - first).dt.days
    original = table.loc[rows, "ac_kw"]
    factor = 1 - rate / 100 * day_number
    table.loc[rows, "ac_kw"] = original * factor
    return {"fault": "soiling", "plant": plant, "inverter": inverter,
            "start": first, "end": pd.Timestamp(table["date"].max()) + pd.Timedelta(days=1),
            "size": round(float(rate), 3),
            "true_kwh": round(float((original * (1 - factor)).sum() * config.INTERVAL_HOURS), 1)}


def pick_days(clean_days, rng):
    """One clean day per inverter, never two inverters of a plant on the same day (fair peer median)."""
    picks, used = [], set()
    candidates = sorted(clean_days)
    rng.shuffle(candidates)
    seen_inverters = set()
    for plant, inverter, date in candidates:
        if (plant, inverter) in seen_inverters or (plant, date) in used:
            continue
        picks.append((plant, inverter, date))
        seen_inverters.add((plant, inverter))
        used.add((plant, date))
    return picks


def score_run(injections, events):
    """Mark each injection caught/missed and count alerts that match no injection (false alarms)."""
    events = events if not events.empty else pd.DataFrame(columns=["plant", "inverter", "fault_type", "start", "end"])
    matched_event_ids = set()
    for record in injections:
        overlap = events[(events["plant"] == record["plant"]) & (events["inverter"] == record["inverter"])
                         & (events["start"] < record["end"]) & (events["end"] > record["start"])]
        target = TARGET_TYPE[record["fault"]]
        right = overlap[overlap["fault_type"] == target]
        matched_event_ids.update(overlap.index)
        record["caught"] = not right.empty
        record["caught_as_other_type"] = right.empty and not overlap.empty
        record["other_types"] = ",".join(sorted(overlap["fault_type"].unique())) if record["caught_as_other_type"] else ""
        if right.empty:
            record.update(delay_minutes=np.nan, estimated_kwh=np.nan)
            continue
        first = right.sort_values("start").iloc[0]
        if target in MIN_INTERVALS_SETTING:
            # Real time: an alert can only be raised once the minimum number of readings is seen.
            ready = first["start"] + INTERVAL * getattr(config, MIN_INTERVALS_SETTING[target])
            record["delay_minutes"] = max((ready - record["start"]) / pd.Timedelta(minutes=1), 0)
        else:
            record["delay_minutes"] = np.nan   # degradation is judged over the whole period
        key = "energy_at_risk_kwh" if target == "DATA_GAP" else "energy_loss_kwh"
        record["estimated_kwh"] = float(sum(ev[key] for ev in right["evidence"]))
    unmatched = events.drop(index=list(matched_event_ids))
    return injections, unmatched


def false_alarms_on_clean_days(events, clean_days):
    """Alerts (per type) that start on an inverter-day we know is healthy and untouched."""
    if events.empty:
        return {}
    on_clean = [(p, i, str(s.date())) in clean_days for p, i, s in zip(events["plant"], events["inverter"], events["start"])]
    return events[on_clean]["fault_type"].value_counts().to_dict()
