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
