"""Central settings for SolarSense: file paths and important constants.

Every other file imports its settings from here, so a number only ever
needs to be changed in one place. Fault-detection thresholds are added in Phase 4.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Folders (built from this file's location, so they work on any laptop)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"              # the 4 Kaggle CSVs — never edited
PROCESSED_DIR = DATA_DIR / "processed"  # files our pipeline creates
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
WEB_DIR = PROJECT_ROOT / "web"

# ---------------------------------------------------------------------------
# Raw input files (Kaggle "Solar Power Generation Data" by anikannal)
# ---------------------------------------------------------------------------
RAW_FILES = {
    "plant_1_generation": RAW_DIR / "Plant_1_Generation_Data.csv",
    "plant_1_weather": RAW_DIR / "Plant_1_Weather_Sensor_Data.csv",
    "plant_2_generation": RAW_DIR / "Plant_2_Generation_Data.csv",
    "plant_2_weather": RAW_DIR / "Plant_2_Weather_Sensor_Data.csv",
}

# The files do NOT all use the same date format, so we state each one
# explicitly instead of letting pandas guess (guessing can swap day/month).
DATE_FORMATS = {
    "plant_1_generation": "%d-%m-%Y %H:%M",       # e.g. 15-05-2020 00:00
    "plant_1_weather": "%Y-%m-%d %H:%M:%S",       # e.g. 2020-05-15 00:00:00
    "plant_2_generation": "%Y-%m-%d %H:%M:%S",
    "plant_2_weather": "%Y-%m-%d %H:%M:%S",
}

PLANTS = [1, 2]

# ---------------------------------------------------------------------------
# Output files (created by later phases)
# ---------------------------------------------------------------------------
CLEAN_FILE = PROCESSED_DIR / "clean.parquet"
EXPECTED_FILE = PROCESSED_DIR / "expected.parquet"
ALERTS_FILE = PROCESSED_DIR / "alerts.parquet"
ALERT_STATUS_FILE = PROCESSED_DIR / "alert_status.json"
METRICS_FILE = REPORTS_DIR / "metrics.json"
DATA_QUALITY_REPORT = REPORTS_DIR / "data_quality.md"
MODEL_CARD = REPORTS_DIR / "model_card.md"
ASSUMPTIONS_REPORT = REPORTS_DIR / "assumptions.md"

# ---------------------------------------------------------------------------
# General constants
# ---------------------------------------------------------------------------
# Fixed random seed so every run gives the same results (reproducible).
RANDOM_SEED = 42

# The data has one reading every 15 minutes = 0.25 hours.
# Energy (kWh) = power (kW) x time (hours), so we multiply by this.
INTERVAL_HOURS = 0.25

# Readings per day: 24 hours x 4 readings per hour.
READINGS_PER_DAY = 96

# A 15-minute slot counts as "daylight" when the weather sensor's irradiation
# is above this value. Small but above zero, so sensor noise at dawn/dusk
# does not count as sunshine. (Irradiation units in this dataset: ~kW/m².)
DAYLIGHT_IRRADIATION_THRESHOLD = 0.02

# Hours we treat as "definitely night" for sanity checks (20:00 to 04:59).
NIGHT_HOURS = [20, 21, 22, 23, 0, 1, 2, 3, 4]

# ASSUMPTION: electricity value used to convert lost energy (kWh) into rupees.
# This is only a placeholder. Set it to a sourced value (e.g. a recent Indian
# solar tariff) and record the source in reports/assumptions.md.
# TODO(team): find and cite a source for this number.
TARIFF_INR_PER_KWH = 3.0

# ---------------------------------------------------------------------------
# Phase 2 — cleaning
# ---------------------------------------------------------------------------
# Plant 1 DC is fixed by a factor COMPUTED from the data (see clean_data.py):
# we use Plant 2 (whose DC looks normal) as the reference plant.
DC_REFERENCE_PLANT = 2
DC_SUSPECT_PLANT = 1

# ---------------------------------------------------------------------------
# Phase 3 — expected-output model
# ---------------------------------------------------------------------------
# First 70% of days train the model, the last 30% test it (time split, never random).
TRAIN_FRACTION = 0.7

# "Obvious outage" (removed from TRAINING only so the model learns healthy
# behaviour): sunlight is clearly strong but the inverter gives almost nothing.
OUTAGE_IRRADIATION_MIN = 0.3   # strong sunlight (noon is ~1.0)
OUTAGE_AC_MAX_KW = 1.0         # inverters make ~1,300 kW per unit of irradiation

# MAPE (average % error) is only measured on rows with meaningful power,
# because a % error on a tiny number (e.g. 2 kW at dawn) is huge and misleading.
MAPE_MIN_ACTUAL_KW = 100.0

# Ratios like actual ÷ expected are only computed when expected is above this,
# to avoid dividing by almost zero at dawn and dusk.
MIN_EXPECTED_KW_FOR_RATIO = 50.0

# Random Forest settings: small enough to train in seconds on a laptop.
RF_N_ESTIMATORS = 100
RF_MAX_DEPTH = 14
RF_MIN_SAMPLES_LEAF = 5

# Model files
MODEL_FILE_TEMPLATE = "plant_{plant}_{model}.joblib"

# ---------------------------------------------------------------------------
# Phase 4 — fault detection (all thresholds in one place)
# ---------------------------------------------------------------------------
# Two flagged readings separated by at most this many un-flagged readings still
# count as ONE event (so one noisy 15-minute reading does not split an alert).
MERGE_GAP_INTERVALS = 1

# INVERTER_TRIP: strong sunlight but (almost) no output.
TRIP_IRRADIATION_MIN = 0.25    # sunlight clearly strong enough to produce power
TRIP_AC_MAX_KW = 1.0           # "almost zero" output
TRIP_MIN_INTERVALS = 2         # at least 30 minutes

# UNDERPERFORMANCE: clearly below expected AND below neighbours (so not a cloud).
UNDER_RESIDUAL_PCT_MAX = -20.0  # actual at least 20% below expected
UNDER_PEER_RATIO_MAX = 0.8      # and at least 20% below the plant median
UNDER_MIN_INTERVALS = 4         # at least 1 hour

# DEGRADATION / SOILING: slow, steady decline of daily performance vs peers.
DEGRADATION_MIN_DAYS = 10            # need enough days for a trend
DEGRADATION_SLOPE_MAX_PCT = -0.3     # falling by at least 0.3% per day...
DEGRADATION_MIN_TOTAL_DECLINE_PCT = 5.0  # ...and at least 5% in total

# DATA_GAP: inverter silent during daylight.
GAP_MIN_INTERVALS = 2          # at least 30 minutes

# OVERHEATING (plant-level: there is only ONE panel-temperature sensor per plant).
OVERHEAT_DELTA_MIN_C = 28.0    # panels this much hotter than the air (top ~1% of readings)
OVERHEAT_PLANT_RATIO_MAX = 0.9 # and the whole plant below 90% of expected
OVERHEAT_MIN_INTERVALS = 2

# SEVERITY: decided by energy lost (kWh) — one inverter makes ~1,000 kWh in a sunny hour.
SEVERITY_LOSS_KWH = [(2000, "Critical"), (500, "High"), (100, "Medium"), (0, "Low")]
# Data gaps have no confirmed loss, so they are rated by daylight hours silent,
# and never above "High" (we cannot prove energy was lost, only that we can't see it).
SEVERITY_GAP_HOURS = [(4, "High"), (1, "Medium"), (0, "Low")]
# An event lasting this long is raised one severity level (long problems matter more).
SEVERITY_LONG_EVENT_HOURS = 4.0
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]

# ---------------------------------------------------------------------------
# Phase 5 — optional "unusual day" score (Isolation Forest)
# ---------------------------------------------------------------------------
# ASSUMPTION: share of inverter-days we expect to be unusual. Isolation Forest
# needs this to decide where "odd" starts; there are no labels to measure it.
ANOMALY_CONTAMINATION = 0.05
ANOMALY_N_ESTIMATORS = 200
ANOMALY_DAYS_FILE = PROCESSED_DIR / "anomaly_days.parquet"

# ---------------------------------------------------------------------------
# Phase 6 — energy and money loss
# ---------------------------------------------------------------------------
DAILY_PLANT_FILE = PROCESSED_DIR / "daily_plant.parquet"
DAILY_INVERTER_FILE = PROCESSED_DIR / "daily_inverter.parquet"
TOP_N_INVERTERS = 5
# ASSUMPTION (estimate): "projected annual loss" scales the observed period to
# a full year, as if every day were like the May–June days in the data.
DAYS_PER_YEAR = 365

# ---------------------------------------------------------------------------
# Phase 7 — validation with injected (synthetic) faults
# ---------------------------------------------------------------------------
VALIDATION_RUNS = 5            # repeats with different seeds (more samples)
VALIDATION_SOILING_RUNS = 10   # soiling runs (2 inverters each)
VALIDATION_INJECTIONS_FILE = PROCESSED_DIR / "validation_injections.parquet"
VALIDATION_TRADEOFF_FILE = PROCESSED_DIR / "validation_tradeoff.parquet"
# Three threshold settings for the sensitivity trade-off test.
VALIDATION_THRESHOLD_SETTINGS = {
    "sensitive": {"UNDER_RESIDUAL_PCT_MAX": -10.0, "UNDER_PEER_RATIO_MAX": 0.9,
                  "UNDER_MIN_INTERVALS": 2, "TRIP_MIN_INTERVALS": 1},
    "default": {},
    "strict": {"UNDER_RESIDUAL_PCT_MAX": -30.0, "UNDER_PEER_RATIO_MAX": 0.7,
               "UNDER_MIN_INTERVALS": 8, "TRIP_MIN_INTERVALS": 4},
}
# Size of each planted fault: (smallest, largest). Durations are picked in 15-minute steps.
VALIDATION_FAULT_SIZES = {
    "trip_hours": (1.0, 4.0),                    # output set to 0 around midday
    "trip_centre_hour": 12,                      # trips are centred on noon (± 1 hour)
    "underperformance_hours": (2.0, 6.0),
    "underperformance_output_kept": (0.6, 0.85), # output multiplied by this
    "data_gap_hours": (1.0, 3.0),                # readings removed
    "soiling_pct_per_day": (0.3, 1.0),           # gradual decline over the test days
    "window_hours": (7, 17),                     # underperformance / gaps happen between 07:00 and 17:00
}
# Groups used to show "what is easy vs hard to catch" (edges of each size group).
VALIDATION_SIZE_BUCKETS = {
    "trip": ("hours", [1, 2, 3, 4.01]),
    "underperformance": ("output kept", [0.6, 0.7, 0.8, 0.851]),
    "data_gap": ("hours", [1, 1.75, 2.5, 3.01]),
    "soiling": ("% per day", [0.3, 0.5, 0.75, 1.01]),
}

# Charts: how many test points to draw in the predicted-vs-actual scatter (keeps the PNG readable).
SCATTER_SAMPLE_POINTS = 5000
