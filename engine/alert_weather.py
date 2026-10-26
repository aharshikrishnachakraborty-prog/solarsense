"""Weather context for fault detection (Phase W4): what was the sky doing during each alert?

Used by engine/detect_faults.py. Two jobs:
1. Attach the sky (label, clear-sky index, variability) and panel temperature to every reading and alert.
2. The weather-aware rule: under a DIFFICULT sky (overcast or quickly changing), one sunlight sensor cannot
   describe the whole plant — a cloud shadow can darken some inverters and not others for a few minutes.
   So a short underperformance event there needs stronger proof before it becomes an alert.
"""

from functools import lru_cache

import numpy as np
import pandas as pd

from engine import config

SKY_COLUMNS = ["sky_label", "clear_sky_index", "variability"]


@lru_cache(maxsize=1)
def _load_sky():
    """The sky columns of weather_15min.parquet, read once (validation calls the detector many times)."""
    if not config.WEATHER_15MIN_FILE.exists():
        return None
    return pd.read_parquet(config.WEATHER_15MIN_FILE, columns=["plant", "timestamp", *SKY_COLUMNS])


def add_sky_context(table):
    """Add sky label, clear-sky index, variability and a 'difficult sky' flag to every reading.

    Without weather files (old pipeline run) the columns are blank and the detector works exactly as before.
    """
    if "sky_label" not in table.columns:
        sky = _load_sky()
        if sky is None:
            table = table.assign(**{column: np.nan for column in SKY_COLUMNS})
        else:
            table = table.merge(sky, on=["plant", "timestamp"], how="left")
    table["difficult_sky"] = ((table["sky_label"] == "Overcast")
                              | (table["variability"] >= config.SKY_HIGH_VARIABILITY))
    return table


def sky_evidence(rows):
    """Sky during an event: most common label, average CSI, share of difficult-sky readings, panel temperature."""
    labels = rows["sky_label"].dropna()
    csi, temps = rows["clear_sky_index"].dropna(), rows["module_temp"].dropna()
    return {"sky_condition": labels.value_counts().idxmax() if len(labels) else None,
            "avg_csi": round(float(csi.mean()), 2) if len(csi) else None,
            "difficult_sky_share": round(float(rows["difficult_sky"].mean()), 2) if len(rows) else 0.0,
            "avg_module_temp_c": round(float(temps.mean()), 1) if len(temps) else None}


def mostly_difficult_sky(evidence):
    """True if most of the event's readings were under a difficult sky."""
    return evidence.get("difficult_sky_share", 0) >= config.UNDER_DIFFICULT_SKY_SHARE


def needs_more_proof(fault_type, evidence):
    """Weather-aware rule: drop a SHORT underperformance event under a difficult sky unless the inverter was far
    below its neighbours. Long events and strong peer gaps are kept — a passing cloud does neither."""
    return (config.WEATHER_AWARE_UNDER and fault_type == "UNDERPERFORMANCE" and mostly_difficult_sky(evidence)
            and evidence["intervals"] < config.UNDER_DIFFICULT_MIN_INTERVALS
            and evidence["avg_peer_ratio"] > config.UNDER_STRONG_PEER_RATIO)
