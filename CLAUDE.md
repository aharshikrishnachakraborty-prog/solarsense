# CLAUDE.md — SolarSense: AI Solar Plant Health Monitor (Meridian DEV-P01)

> Claude Code reads this file automatically at the start of every session.
> It is the single source of truth for this project. Follow it exactly.
> ("SolarSense" is a placeholder name — the team may rename it.)

---

## 1. Who you are working with

- A team of **first-year B.Tech students** with **little programming experience**.
- They will **present this to hackathon judges** and must be able to explain every part.
- **Simple, readable, commented code beats clever code. Always.**
- After every task, explain what you did **in plain language**, as if to an 18-year-old beginner.

---

## 2. The problem (DEV-P01, Meridian — Application Development track)

Solar operators learn about underperforming panels or inverters **only after losses pile up**.

**Build an app that:** takes plant generation data, compares it with the **expected output given the
weather**, and **flags likely faults with an estimated energy loss**.

### Required deliverables (from the problem statement)
1. **Dashboard of actual vs expected output.**
2. **Anomaly flags with a reason.**
3. **Estimated loss** (energy in kWh, and money in ₹ using a configurable tariff).
4. **Alert list.**

Suggested strategy: time-series anomaly detection or regression against irradiance, with a simple dashboard.
Target users: plant operators, O&M (operations & maintenance) engineers.

### Our product = two parts
- **AI engine (Python)** — cleans data, learns expected output, detects and explains faults, estimates loss,
  validates itself, and serves everything through a **REST API (FastAPI)**.
- **Web dashboard (HTML/CSS/JavaScript + Chart.js)** — a real, working website served by the same
  FastAPI app, used by operators to monitor the plant and act on alerts.

---

## 3. HARD RULES (never break these)

1. **No paid APIs, no paid services, no API keys.** Runs free on a normal laptop (8 GB RAM).
   *Exception (team decision, 2026-10-29):* the optional chat assistant uses a FREE Google Gemini API key,
   kept only in `.env` (gitignored), never in code or the browser.
   The whole app must keep working when the assistant is off.
2. **Never invent numbers.** Every number shown in the UI or slides must be computed by our code and saved in
   `reports/metrics.json` or served by the API from computed files. Assumptions are labelled `ASSUMPTION`
   in code, UI (small ⓘ note) and `reports/assumptions.md`.
3. **Honest evaluation.** Train the expected-output model on earlier days, test on later days (time split,
   never random). Validate fault detection with **injected synthetic faults** (see Phase 7) and report
   precision/recall honestly, including what we miss.
4. **The dashboard never computes ML itself.** The pipeline precomputes results into files; the API reads them
   and returns JSON; the frontend only displays. The demo must be fast and never crash.
5. **Frontend stays simple:** plain HTML + CSS + vanilla JavaScript + Chart.js from a CDN.
   **No React, no build tools, no npm**, unless the team explicitly asks.
6. **Ask before** adding any library not listed in Section 5, deleting files, or big structural changes.
7. **Before writing code for a phase, show a short plan (bullets) and wait for "OK".**
8. Keep each file **under ~250 lines**; split if bigger.
9. **The LLM is never the decision maker.** Fault detection is done by models and rules. An optional local LLM
   (Ollama) may only rephrase computed facts into friendly sentences; everything must work with it off.
10. Do not use any real company's logo or branding in the UI.

---

## 4. Data

### Main dataset — Kaggle "Solar Power Generation Data" (by anikannal)
- Two solar plants in India, **34 days** (15 May – 17 Jun 2020), readings every **15 minutes**.
- 4 CSV files:
  - `Plant_1_Generation_Data.csv`, `Plant_2_Generation_Data.csv` — per inverter:
    `DATE_TIME, PLANT_ID, SOURCE_KEY (inverter id), DC_POWER, AC_POWER, DAILY_YIELD, TOTAL_YIELD`
  - `Plant_1_Weather_Sensor_Data.csv`, `Plant_2_Weather_Sensor_Data.csv` — per plant:
    `DATE_TIME, PLANT_ID, SOURCE_KEY, AMBIENT_TEMPERATURE, MODULE_TEMPERATURE, IRRADIATION`
- ~22 inverters per plant. Verify all column names and counts after loading — don't assume.
- **Known quirks (turn them into features, not bugs):**
  - Date formats differ between files (e.g. `15-05-2020 00:00` vs `2020-05-15 00:00:00`). Parse each file carefully.
  - Plant 1's DC_POWER looks ~10× too large (DC→AC ratio ≈ 9.8%, impossible). Detect it, document it in
    `reports/data_quality.md`, and correct with a clearly labelled scaling factor (ASSUMPTION).
  - Some Plant 2 inverters have missing readings (~25%). Treat as a **"Data gap / communication loss"** alert type.
  - Night-time rows (irradiation ≈ 0) should be excluded from performance analysis.
- Raw files live in `data/raw/` and are never edited. The team downloads them manually from Kaggle (free account).
- Plant GPS location is **not** in the dataset — never claim it.

Credit the data source and licence on the dashboard "About" page.

---

## 5. Tech stack (free, beginner-explainable)

| Purpose | Tool | How to explain it to judges |
|---|---|---|
| Data | pandas, numpy, pyarrow | "Excel, but in Python" |
| Expected-output model | scikit-learn: physics-style linear model (baseline) + `RandomForestRegressor` | "Learns how much power the plant *should* make for this sunlight and temperature" |
| Peer comparison | pandas (median of all inverters at the same time) | "Compare each inverter with its neighbours under the same sun" |
| Anomaly detection | residual thresholds + rolling windows + simple rules; optional `IsolationForest` | "Flag when actual is far below expected for too long" |
| Trend (soiling/dust) | rolling performance ratio + linear trend | "Slow, steady decline = dust or ageing" |
| API | FastAPI + uvicorn + pydantic | "The engine's waiter: frontend asks, API answers with data" |
| Frontend | HTML, CSS, vanilla JS, Chart.js (CDN) | "The website the operator sees" |
| Optional summaries | Ollama local model (e.g. `llama3.2:3b`) + template fallback | "Free offline AI that turns facts into sentences" |
| Models | joblib | Saved model files |
| Tests | pytest, FastAPI TestClient | Checks that nothing is broken |

Python 3.10–3.12. Pin versions in `requirements.txt`.

---

## 6. Project structure (keep to this)

```
solarsense/
├── CLAUDE.md
├── PROMPTS.md
├── PROGRESS.md              # updated after every phase
├── README.md
├── requirements.txt
├── run_all.py               # whole pipeline end-to-end
├── data/
│   ├── raw/                 # 4 Kaggle CSVs (never edited)
│   └── processed/           # cleaned data, expected output, alerts, losses
├── models/
├── reports/
│   ├── metrics.json         # every number shown anywhere comes from here
│   ├── data_quality.md
│   ├── model_card.md
│   ├── assumptions.md
│   └── figures/
├── engine/                  # the AI app (Python)
│   ├── config.py            # paths, thresholds, tariff, seed=42
│   ├── load_data.py
│   ├── clean_data.py
│   ├── expected_model.py
│   ├── detect_faults.py
│   ├── losses.py
│   ├── validate.py          # synthetic fault injection tests
│   └── summaries.py         # templates + optional Ollama
├── api/
│   ├── main.py              # FastAPI app, also serves the frontend
│   └── routes/ (optional split)
├── web/                     # the dashboard website
│   ├── index.html           # Overview
│   ├── plant.html
│   ├── inverter.html
│   ├── alerts.html
│   ├── about.html
│   ├── css/style.css
│   └── js/ (api.js, charts.js, one file per page)
└── tests/
```

---

## 7. Key definitions (use these words consistently)

- **Inverter:** device converting panel DC power to AC power; our unit of monitoring (`SOURCE_KEY`).
- **Irradiation:** strength of sunlight hitting panels (from the weather sensor).
- **Expected power:** what an inverter *should* produce at this irradiation and module temperature (model output).
- **Residual / deviation:** `actual − expected` (and % of expected).
- **Performance ratio (PR):** `actual energy ÷ expected energy` over a period (1.0 = perfect).
- **Energy loss (kWh):** sum of `max(expected − actual, 0)` × interval hours (0.25 h) during daylight.
- **Money loss (₹):** energy loss × tariff (₹/kWh) — tariff is a configurable ASSUMPTION.
- **Alert:** a detected fault event with type, inverter, start/end time, severity, reason, evidence, energy & ₹ loss,
  recommended action, status (Open / Acknowledged / Resolved).

### Fault types we detect
| Type | Simple rule idea | Typical cause / action |
|---|---|---|
| **Inverter trip / outage** | Strong sunlight but AC power ≈ 0 for ≥ N intervals | Inverter fault, grid trip → send technician |
| **Underperformance** | Actual < expected by > X% for ≥ N intervals, and below peer median | Partial string failure, shading → inspect strings |
| **Gradual degradation / soiling** | Daily PR declining trend over days vs peers | Dust → schedule cleaning |
| **Data gap / comms loss** | Missing readings during daylight | Logger/network issue → check communication |
| **Overheating** | Module temp very high vs ambient + low efficiency | Ventilation / hotspot → thermal check |
| **Sensor/data issue** | Impossible values (e.g. DC→AC ratio) | Recalibrate sensor |

All thresholds live in `engine/config.py` with comments.

---

## 8. Workflow for every phase

1. Read `CLAUDE.md` and `PROGRESS.md`.
2. Show a short plan → wait for "OK".
3. Build in small steps; run the code; fix errors yourself.
4. Run the phase's acceptance checks (in PROMPTS.md).
5. Save numbers to `reports/metrics.json` (merge — don't overwrite other sections).
6. Update `PROGRESS.md`.
7. End with **"Explain it simply"**: what was built (3–5 sentences, no jargon), files changed, how to check it
   yourself, and 2 likely judge questions with short honest answers.

---

## 9. Code style

- Docstring on every function (one simple sentence). Comments explain *why*.
- Clear names (`energy_loss_kwh`, not `el`). Constants in `engine/config.py`. Seed 42.
- Friendly error messages (e.g. "Raw data not found — download the 4 Kaggle CSVs into data/raw/").
- JavaScript: one small file per page, shared fetch helpers in `web/js/api.js`, no frameworks.

---

## 10. Dashboard design rules

- Looks like a professional monitoring product: clean, calm, one accent colour (solar amber), status colours
  (green OK / amber warning / red critical), consistent cards and spacing.
- Top navigation bar on every page; plant selector (Plant 1 / Plant 2); "Replay date" selector.
- Every page starts with a **one-line plain-English takeaway** from the API (e.g. "3 inverters need attention —
  estimated loss ₹X today").
- KPI cards: big number + small comparison.
- Every chart: insight title, axis labels with units, legend, tooltips.
- Every alert has a **"Why?"** section showing the evidence chart and numbers.
- Assumptions shown with ⓘ tooltips.
- Responsive: works on a laptop (1366×768) and a phone.
- Loading states and friendly error messages if the API is down.

---

## 11. Definition of done

- `python run_all.py` rebuilds everything from raw data without errors.
- `uvicorn api.main:app --reload` → open `http://localhost:8000` → all pages work.
- `pytest` passes.
- `reports/metrics.json` contains data-quality stats, model accuracy vs baseline, detection precision/recall on
  injected faults, total losses by plant and fault type.
- `reports/model_card.md`, `reports/assumptions.md`, `reports/data_quality.md` are complete and honest.
- README: beginner setup in ≤ 10 steps.
