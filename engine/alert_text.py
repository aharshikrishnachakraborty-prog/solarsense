"""Turn a detected fault event into human words: reason sentence, severity and action.

Every number in a reason sentence comes from the event's evidence dictionary.
"""

from engine import config

RECOMMENDED_ACTIONS = {
    "INVERTER_TRIP": "Send a technician to check the inverter and grid connection; restart if safe.",
    "UNDERPERFORMANCE": "Inspect the strings feeding this inverter for failed strings, loose connectors or shading.",
    "DEGRADATION": "Schedule panel cleaning; if output does not recover, check for module ageing.",
    "DATA_GAP": "Check the data logger and network/communication link for this inverter.",
    "OVERHEATING": "Run a thermal check: ventilation, hotspots and inverter cooling.",
    "SENSOR_ISSUE": "Recalibrate or replace the sensor/meter and fix the data logging.",
}


def _fmt(number, decimals=0):
    """Format a number with thousands separators, e.g. 1234.5 -> '1,235'."""
    return f"{number:,.{decimals}f}"


def _peer_sentence(others_down_pct):
    """Explain whether neighbouring inverters were fine at the same time."""
    if others_down_pct < 20:
        return f"Neighbouring inverters produced normally (only {_fmt(others_down_pct)}% were also down)."
    if others_down_pct >= 50:
        return (f"{_fmt(others_down_pct)}% of the other inverters were also down at the same time — "
                "likely a plant- or grid-level trip rather than this inverter alone.")
    return f"{_fmt(others_down_pct)}% of the other inverters were also down at the same time."


def make_reason(fault_type, ev):
    """Write a plain-English reason sentence with real numbers for one alert."""
    hours = _fmt(ev["duration_hours"], 2).rstrip("0").rstrip(".")
    hours = "1 hour" if hours == "1" else f"{hours} hours"
    if fault_type == "INVERTER_TRIP":
        return (f"Output was {_fmt(ev['avg_actual_kw'], 1)} kW on average for {hours} while sunlight was "
                f"strong (avg irradiation {ev['avg_irradiation']:.2f}); about {_fmt(ev['avg_expected_kw'])} kW "
                f"was expected. " + _peer_sentence(ev["others_down_pct"]))
    if fault_type == "UNDERPERFORMANCE":
        return (f"Output was {_fmt(-ev['avg_residual_pct'])}% below expected for {hours} "
                f"(avg {_fmt(ev['avg_actual_kw'])} kW vs {_fmt(ev['avg_expected_kw'])} kW expected) and "
                f"{_fmt(100 * (1 - ev['avg_peer_ratio']))}% below neighbouring inverters under the same sunlight.")
    if fault_type == "DEGRADATION":
        return (f"Performance compared with neighbours fell steadily by {abs(ev['slope_pct_per_day']):.2f}% per "
                f"day over {ev['days']} days (from {_fmt(ev['start_relative_pct'], 1)}% to "
                f"{_fmt(ev['end_relative_pct'], 1)}% of the plant median) — typical of dust/soiling or ageing.")
    if fault_type == "DATA_GAP":
        return (f"No readings for {hours} ({ev['intervals']} readings) during daylight. About "
                f"{_fmt(ev['energy_at_risk_kwh'])} kWh of expected energy could not be verified.")
    if fault_type == "OVERHEATING":
        return (f"Panels were {_fmt(ev['avg_temp_delta_c'], 1)} °C hotter than the air (avg panel temperature "
                f"{_fmt(ev['avg_module_temp_c'], 1)} °C) and the whole plant produced only "
                f"{_fmt(100 * ev['avg_plant_ratio'])}% of expected for {hours}.")
    if fault_type == "SENSOR_ISSUE":
        return ev["description"]
    raise ValueError(f"Unknown fault type: {fault_type}")


def _level_from_table(value, table):
    """Pick the first severity whose threshold the value reaches (tables go from high to low)."""
    for threshold, level in table:
        if value >= threshold:
            return level
    return "Low"


def make_severity(fault_type, ev):
    """Severity from energy lost (or daylight hours silent for gaps), raised one level for long events."""
    if fault_type == "SENSOR_ISSUE":
        return ev["severity"]
    if fault_type == "DATA_GAP":
        level = _level_from_table(ev["duration_hours"], config.SEVERITY_GAP_HOURS)
    else:
        level = _level_from_table(ev["energy_loss_kwh"], config.SEVERITY_LOSS_KWH)
    # Degradation spans days by nature, so the "long event" bump would always apply — skip it.
    long_event = fault_type != "DEGRADATION" and ev["duration_hours"] >= config.SEVERITY_LONG_EVENT_HOURS
    if long_event and fault_type != "DATA_GAP":
        index = min(config.SEVERITY_LEVELS.index(level) + 1, len(config.SEVERITY_LEVELS) - 1)
        level = config.SEVERITY_LEVELS[index]
    return level


# --- Phase W4: confidence and the weather sentence ------------------------------
def _sky_words(ev):
    """'clear (CSI 0.92)' — the sky during the alert in words, or None if there was no weather reading."""
    if not ev.get("sky_condition"):
        return None
    csi = f" (clear-sky index {ev['avg_csi']:.2f})" if ev.get("avg_csi") is not None else ""
    return f"{ev['sky_condition'].lower()}{csi}"


def _difficult(ev):
    """Most of the alert happened under an overcast or quickly changing sky."""
    return ev.get("difficult_sky_share", 0) >= config.UNDER_DIFFICULT_SKY_SHARE


def make_confidence(fault_type, ev):
    """High / Medium / Low: how sure we are, from the sky during the alert and the peer evidence."""
    if fault_type in ("DATA_GAP", "SENSOR_ISSUE"):
        return "High"            # missing or impossible readings are facts, not estimates
    if fault_type in ("DEGRADATION", "OVERHEATING"):
        return "Medium"          # a trend over days / only one panel-temperature sensor per plant
    if fault_type == "INVERTER_TRIP":
        return "Medium" if _difficult(ev) else "High"   # near-zero output in measured sunlight
    if not ev.get("sky_condition"):
        level = "Medium"
    elif _difficult(ev):
        level = "Low"
    else:
        level = "High" if ev["sky_condition"] == "Clear" else "Medium"
    if ev["avg_peer_ratio"] <= config.UNDER_STRONG_PEER_RATIO:   # far below neighbours under the same sky
        level = config.CONFIDENCE_LEVELS[min(config.CONFIDENCE_LEVELS.index(level) + 1, 2)]
    return level


def make_weather_note(fault_type, ev):
    """One sentence on the weather during the alert, e.g. 'Sky was clear (...), so low output is NOT clouds.'"""
    if fault_type == "SENSOR_ISSUE":
        return "Data-quality issue measured over the whole period — not related to the weather."
    if fault_type == "DEGRADATION":
        return ("Judged over many days against neighbouring inverters, which see the same clouds and heat, "
                "so the weather cancels out.")
    sky = _sky_words(ev)
    if sky is None:
        return "No weather reading during this alert, so the sky cannot be checked."
    temp = f" and panels at {ev['avg_module_temp_c']:.0f} °C" if ev.get("avg_module_temp_c") is not None else ""
    below = f"{_fmt(100 * (1 - ev['avg_peer_ratio']))}% below" if ev.get("avg_peer_ratio") is not None else ""
    if fault_type == "INVERTER_TRIP":
        return f"Sky was {sky}{temp} — there was usable sunlight, so near-zero output is NOT caused by clouds."
    if fault_type == "DATA_GAP":
        sun = ("good sunlight, so energy was probably made but not recorded" if (ev.get("avg_csi") or 0) >= 0.5
               else "weak sunlight, so little energy was at stake")
        return f"Sky was {sky}{temp} during the gap — {sun}."
    if fault_type == "OVERHEATING":
        return f"Sky was {sky}{temp} while the whole plant fell short."
    csi = f" (clear-sky index {ev['avg_csi']:.2f})" if ev.get("avg_csi") is not None else ""
    if _difficult(ev):
        kind = "Overcast" if ev["sky_condition"] == "Overcast" else f"Quickly changing, {ev['sky_condition'].lower()}"
        return (f"{kind} sky{csi} — sunlight was uneven across the plant, so confidence is lower; this inverter "
                f"was still {below} its neighbours under the same sky.")
    if ev["sky_condition"] == "Clear":
        return f"Sky was {sky}{temp}, so low output is NOT caused by clouds."
    return (f"{ev['sky_condition']} sky{csi} — confirmed by comparison with neighbouring inverters "
            f"({below} them under the same clouds).")
