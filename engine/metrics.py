"""Read and update reports/metrics.json — the single home of every number we show."""

import json

from engine import config


def load_metrics():
    """Return the current contents of metrics.json (empty dict if it does not exist yet)."""
    if not config.METRICS_FILE.exists() or config.METRICS_FILE.stat().st_size == 0:
        return {}
    with open(config.METRICS_FILE, encoding="utf-8") as file:
        return json.load(file)


def save_metrics_section(section, values):
    """Replace ONE section (e.g. "data") in metrics.json, keeping all other sections."""
    metrics = load_metrics()
    metrics[section] = values
    with open(config.METRICS_FILE, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)
