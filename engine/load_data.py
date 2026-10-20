"""Load the 4 raw Kaggle CSV files into pandas tables with correct dates.

The raw files are only ever READ here, never changed.
"""

import pandas as pd

from engine import config


def _read_raw_csv(file_key):
    """Read one raw CSV and turn its DATE_TIME text into real dates."""
    path = config.RAW_FILES[file_key]
    if not path.exists():
        raise FileNotFoundError(
            f"Raw data not found: {path.name}. "
            "Download the 4 Kaggle CSVs into data/raw/ (see README.md)."
        )
    table = pd.read_csv(path)
    # Each file has its own date format, so we use the exact one from config.
    # errors="raise" means a badly formatted date stops us loudly instead of
    # silently becoming a blank value.
    table["DATE_TIME"] = pd.to_datetime(
        table["DATE_TIME"], format=config.DATE_FORMATS[file_key], errors="raise"
    )
    return table


def load_generation(plant):
    """Load the power readings of every inverter of one plant (1 or 2)."""
    return _read_raw_csv(f"plant_{plant}_generation")


def load_weather(plant):
    """Load the weather sensor readings (sunlight, temperatures) of one plant."""
    return _read_raw_csv(f"plant_{plant}_weather")


def load_all():
    """Load all 4 files and return them in a dictionary keyed like config.RAW_FILES."""
    tables = {}
    for plant in config.PLANTS:
        tables[f"plant_{plant}_generation"] = load_generation(plant)
        tables[f"plant_{plant}_weather"] = load_weather(plant)
    return tables
