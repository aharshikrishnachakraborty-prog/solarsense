# SolarSense — AI Solar Plant Health Monitor

Meridian hackathon, problem DEV-P01. SolarSense compares what each solar inverter **actually** produced
with what it **should** have produced given the weather, flags likely faults with a plain-English reason,
and estimates the energy (kWh) and money (₹) lost.

> Work in progress — see `PROGRESS.md` for the current status.

## Setup (Windows, PowerShell)

1. Install **Python 3.12** (3.10–3.12 work; 3.13+ is not supported).
2. Open a terminal in the `solarsense/` folder.
3. Create a virtual environment: `py -3.12 -m venv .venv`
4. Activate it: `.venv\Scripts\Activate.ps1` (you should see `(.venv)` at the start of the line)
5. Install the libraries: `pip install -r requirements.txt`
6. Download the 4 CSVs of the Kaggle dataset **"Solar Power Generation Data"** (by anikannal) into `data/raw/`.

More steps (running the pipeline and the dashboard) will be added as we build them.

## Data sources
- Kaggle — "Solar Power Generation Data" by anikannal (two plants in India, May–June 2020).
