"""Write the plain-English sentence for one day's sky (Phase W1), e.g.
"Mostly clear morning, passing clouds after 2 PM — 18% less sunlight than a clear day."

Only describes labels and numbers already computed in engine/weather.py — it never decides anything itself.
"""

import numpy as np

from engine import config

# Short words for the day's sentence, e.g. "Mostly clear morning, clouds after 2 PM".
ALL_DAY_TEXT = {"Clear": "Clear sky all day", "Partly cloudy": "Partly cloudy all day",
                "Cloudy": "Cloudy most of the day", "Overcast": "Overcast most of the day"}
CLOUDS_ARRIVE_TEXT = {"Partly cloudy": "passing clouds", "Cloudy": "clouds", "Overcast": "overcast"}


def indian(value):
    """Whole number with Indian digit grouping, rounding .5 up, like the dashboard (e.g. 1,42,478)."""
    digits = str(int(np.floor(value + 0.5)))
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    return ",".join([head[max(i - 2, 0):i] for i in range(len(head), 0, -2)][::-1] + [tail])


def format_time(timestamp):
    """12:00 → '12 PM', 14:30 → '2:30 PM' (works on Windows, unlike strftime('%-I'))."""
    hour12 = timestamp.hour % 12 or 12
    suffix = "AM" if timestamp.hour < 12 else "PM"
    return f"{hour12} {suffix}" if timestamp.minute == 0 else f"{hour12}:{timestamp.minute:02d} {suffix}"


def best_split(labelled, clear_first):
    """Time that best splits the day into a clear part and a cloudy part (or cloudy → clear).

    For every possible split time we count readings that fit the story ("clear before, not clear after")
    and keep the time with the most. Returns (time, labels after it) or None if the second part is too short.
    """
    is_clear = (labelled["sky_label"] == "Clear").to_numpy()
    first_part = is_clear if clear_first else ~is_clear
    fits_before = np.concatenate([[0], np.cumsum(first_part)])[:-1]             # fitting readings before split
    fits_after = np.cumsum((~first_part)[::-1])[::-1]                            # fitting readings from split on
    split = int(np.argmax(fits_before + fits_after))
    if len(labelled) - split < config.SKY_CHANGE_MIN_SLOTS or split == 0:
        return None
    return labelled["timestamp"].iloc[split], labelled["sky_label"].iloc[split:]


def dominant(labels):
    """Most common sky label (ties go to the clearer label, the order of SKY_LABELS)."""
    return labels.value_counts().reindex(config.SKY_LABELS, fill_value=0).idxmax()


def describe_day(sky_rows, sunshine_score, coverage_pct):
    """Plain-English sentence for one day, e.g. 'Mostly clear morning, clouds after 2 PM — 18% less sunlight ...'."""
    labelled = sky_rows.dropna(subset=["sky_label"])
    if labelled.empty:
        return "No sunlight readings this day (weather sensor offline)."
    morning = labelled[labelled["hour"] < 12]
    afternoon = labelled[labelled["hour"] >= 12]
    am = dominant(morning["sky_label"]) if len(morning) else dominant(afternoon["sky_label"])
    pm = dominant(afternoon["sky_label"]) if len(afternoon) else am
    if am == pm == "Clear":
        text = ALL_DAY_TEXT[am]
        split = best_split(labelled, clear_first=True)
        # A clear day can still cloud over late; mention it if the cloudy part is mostly cloudy.
        if split is not None and split[0].hour >= 12 and (split[1] != "Clear").mean() >= config.LATE_CLOUDS_MIN_SHARE:
            later = dominant(split[1][split[1] != "Clear"])
            text = f"Clear most of the day, {CLOUDS_ARRIVE_TEXT[later]} after {format_time(split[0])}"
    elif am == pm:
        text = ALL_DAY_TEXT[am]
    elif "Clear" in (am, pm):
        clearing = am != "Clear"
        split = best_split(labelled, clear_first=not clearing)
        start = f"{am} morning" if clearing else "Mostly clear morning"
        after = "clearing" if clearing else CLOUDS_ARRIVE_TEXT[pm]
        text = (f"{start}, {after} after {format_time(split[0])}" if split is not None
                else f"{start}, {pm.lower()} afternoon")
    else:
        text = f"{am} morning, {pm.lower()} afternoon"
    if sunshine_score >= config.SUNSHINE_AS_CLEAR_MIN:
        text += " — about as much sunlight as a clear day"
    else:
        text += f" — {100 - sunshine_score:.0f}% less sunlight than a clear day"
    if coverage_pct < config.SKY_MIN_COVERAGE_PCT:
        text += f" (weather sensor missed {100 - coverage_pct:.0f}% of daylight readings)"
    return text + "."


def describe_temperature(day):
    """Plain-English sentence, e.g. 'Panels reached 61 °C at 1 PM — heat cost about 4% of today's energy (...)'."""
    if day["max_module_c"] != day["max_module_c"]:          # NaN: no panel temperature readings at all
        return "No panel temperature readings this day (weather sensor offline)."
    text = f"Panels reached {day['max_module_c']:.0f} °C at {format_time(day['max_module_time'])}"
    if day["heat_loss_kwh"] <= 0:
        return text + " — panels stayed cool, so heat cost no energy today."
    text += f" — heat cost about {day['heat_loss_pct']:.0f}% of today's energy ({indian(day['heat_loss_kwh'])} kWh"
    text += f", ₹{indian(day['heat_loss_inr'])} at the assumed tariff)"
    if day["hot_hours"] > 0:
        text += f"; {day['hot_hours']:g} h above {config.HOT_MODULE_TEMP_C:.0f} °C"
    return text + "."

