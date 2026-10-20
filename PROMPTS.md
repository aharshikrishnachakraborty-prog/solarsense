# PROMPTS.md — Step-by-step build guide for SolarSense (DEV-P01)

How to use:
1. Create a folder `solarsense/` and put **CLAUDE.md** and **PROMPTS.md** inside.
2. Download the 4 CSVs of Kaggle "Solar Power Generation Data" (by anikannal) into `solarsense/data/raw/`
   (free Kaggle account → dataset page → Download → unzip).
3. Open a terminal in `solarsense/` and start Claude Code (`claude`).
4. Paste **one phase at a time**. Claude shows a plan → reply **"OK"**.
5. Do the **"You check"** list before moving on. The phase owner then runs the learning prompt (end of file).

Team roles (suggested):
- **P1 – Data & Problem** (Phases 1–2)
- **P2 – AI Model & Fault Detection** (Phases 3–5)
- **P3 – Losses, Validation & API** (Phases 6–8)
- **P4 – Web Dashboard & Pitch** (Phases 9–14)

Timeline (~7 days): Day 1 → Ph 0–2 · Day 2 → Ph 3–4 · Day 3 → Ph 5–6 · Day 4 → Ph 7–8 · Day 5 → Ph 9–10 · Day 6 → Ph 11–12 · Day 7 → Ph 13–14.
Optional extras: Phase 11 parts B/C.

---

## Phase 0 — Setup (everyone)

```
"""Read CLAUDE.md fully. We are total beginners.

1. Check my Python version (need 3.10–3.12). If missing, tell me how to install it for my OS and wait.
2. Create a virtual environment .venv and tell me how to activate it on my OS.
3. Create the folder structure from CLAUDE.md Section 6 (empty files OK), a .gitignore (.venv, __pycache__, data/raw) and a basic README.md.
4. Create requirements.txt pinned to recent stable versions: pandas, numpy, pyarrow, scikit-learn, joblib, fastapi, uvicorn[standard], pydantic, requests, pytest, httpx. Install them.
5. Create PROGRESS.md with a checklist of Phases 0–14 from PROMPTS.md.
6. Create engine/config.py with all paths, RANDOM_SEED = 42, INTERVAL_HOURS = 0.25, and a TARIFF_INR_PER_KWH placeholder marked ASSUMPTION.
7. Check that the 4 CSV files exist in data/raw/; if not, give me exact steps to download them from Kaggle.

Show your plan first and wait for OK. At the end explain simply what a virtual environment and requirements.txt are.
```

**You check:** `.venv` active · `pip list` shows fastapi and pandas · 4 CSVs present in `data/raw/`.

---"""

## Phase 1 — Load and understand the data (owner: P1)

```
"""Read CLAUDE.md Section 4. Write engine/load_data.py and a short exploration script, then run it.

1. Load all 4 CSVs, parsing DATE_TIME correctly for EACH file (formats differ — check them).
2. For each file report: rows, columns, date range, number of inverters (SOURCE_KEY), missing values.
3. For each plant: expected number of 15-minute readings per inverter for 34 days vs actual — list inverters with the most missing daylight readings.
4. Check the DC→AC ratio per plant (AC_POWER / DC_POWER in daylight). Confirm or reject the "Plant 1 DC is ~10× too large" quirk with numbers.
5. Check for impossible values: negative power, AC > DC, irradiation > 0 at night, DAILY_YIELD resets.
6. Write reports/data_quality.md for beginners: every column in plain English, each issue found, its size, and how we will handle it.
7. Save stats under "data" in reports/metrics.json.

Explain the 4 files to me simply, and the 3 most important data-quality findings.
```

**You check:** read `reports/data_quality.md` · P1 can explain inverter, irradiation, DC vs AC, DAILY_YIELD.

---"""

## Phase 2 — Clean and merge (owner: P1)

```
Read CLAUDE.md. Write engine/clean_data.py that creates data/processed/clean.parquet:

1. Merge each plant's generation rows (per inverter) with that plant's weather rows on DATE_TIME.
2. Fix Plant 1 DC scaling with a factor computed from the data (label ASSUMPTION, document in reports/assumptions.md).
3. Add columns: plant, inverter, timestamp, date, hour, is_daylight (irradiation above a small threshold in config), dc_kw, ac_kw, irradiation, module_temp, ambient_temp.
4. Build a complete 15-minute time grid per inverter so MISSING readings become explicit rows with a flag `is_missing = True` (needed later for data-gap alerts). Do not fill missing power with fake values.
5. Remove/flag impossible values and count them.
6. Tests in tests/test_clean.py: no duplicate (inverter, timestamp), timestamps every 15 min, is_missing correct, no negative power.

Run it and the tests. Explain simply why we keep missing readings as explicit rows instead of deleting them.
```

**You check:** `pytest` passes · row counts make sense (≈ 34 days × 96 readings × inverters).

---

## Phase 3 — Expected-output model (AI core) (owner: P2)

```
Read CLAUDE.md Sections 3 and 7. Write engine/expected_model.py that predicts how much AC power each inverter SHOULD produce.

1. Use daylight, non-missing rows. Time split per plant: first ~70% of days = train, last ~30% = test. Print both date ranges.
2. Remove obvious outages from TRAINING only (e.g. AC ≈ 0 while irradiation is strong) so the model learns "healthy" behaviour. Report how many rows were removed.
3. Model A (baseline, physics-style): ac_kw ≈ k × irradiation × (1 − γ × (module_temp − 25)), fitted per plant (simple linear regression on engineered features). Explain the formula in a comment.
4. Model B: RandomForestRegressor per plant with features: irradiation, module_temp, ambient_temp, hour, plus inverter id encoded (so it learns each inverter's normal capacity). Keep it fast on a laptop.
5. Evaluate on the test days: MAE (kW), R², and MAPE on rows with meaningful power. Compare A vs B honestly and pick the better one per plant (store the choice in config/metrics).
6. Add expected_kw, residual_kw, residual_pct to every daylight row for ALL days → data/processed/expected.parquet.
7. Peer comparison: for every timestamp, compute the plant-wide median ratio actual/expected across inverters, and each inverter's ratio relative to that median (peer_ratio). This makes detection robust to clouds and sensor error.
8. Save models to models/, metrics under "expected_model" in reports/metrics.json, and write reports/model_card.md for beginners (what, data, features, accuracy vs baseline, limitations).
9. Export 2 PNG charts to reports/figures/: actual vs expected for one healthy day; predicted vs actual scatter.

Explain simply: how Random Forest regression works, what R² means, why we compare with the physics baseline, and why peer comparison helps.
```

**You check:** R² is good but not perfect (≈ 1.00 means something is wrong) · P2 can explain "expected power".

---

## Phase 4 — Fault detection with reasons (owner: P2)

```
Read CLAUDE.md Section 7 (fault types table). Write engine/detect_faults.py.

Using data/processed/expected.parquet and clean.parquet, detect these fault types per inverter, with all thresholds in engine/config.py (commented):
1. INVERTER_TRIP — irradiation strong but ac_kw ≈ 0 for ≥ N consecutive intervals.
2. UNDERPERFORMANCE — residual_pct below −X% AND peer_ratio below Y for ≥ N consecutive intervals.
3. DEGRADATION / SOILING — daily performance ratio (actual energy ÷ expected energy) shows a declining trend over ≥ D days relative to peers (slope from a simple linear fit, with minimum size).
4. DATA_GAP — missing readings during daylight for ≥ N intervals.
5. OVERHEATING — module_temp − ambient_temp above threshold together with below-expected efficiency.
6. SENSOR_ISSUE — impossible values found in cleaning (plant-level).

Merge consecutive flagged intervals into ONE alert event. Each alert must have:
id, plant, inverter, fault_type, start, end, duration_hours, severity (Low/Medium/High/Critical based on loss and duration — rules in config), reason (plain-English sentence with real numbers, e.g. "Output was 0 kW for 2.5 hours while sunlight was strong (avg 0.8). Neighbouring inverters produced normally."), evidence (key numbers), recommended_action (from the table in CLAUDE.md), status = "Open".

Save to data/processed/alerts.parquet and counts per type under "alerts" in reports/metrics.json.

Show me 5 example alerts (one per type found) and explain simply how one rule works, step by step.
```

**You check:** read 10 alerts — every reason sentence makes sense and contains real numbers.

---

## Phase 5 — Optional extra AI check (owner: P2)

```
Read CLAUDE.md. Add an unsupervised anomaly score to engine/detect_faults.py using sklearn IsolationForest on per-inverter-per-day features (performance ratio, peer ratio, residual stats, missing %, temperature delta).

- Use it ONLY as an extra "unusual day" signal shown in the UI, not as the main detector.
- Report how many days it flags and how much it overlaps with our rule-based alerts.
- Explain simply what Isolation Forest does ("finds the odd ones out").

If this makes things confusing or adds little value, tell me honestly and we can skip it.
```

---

## Phase 6 — Energy and money loss (owner: P3)

```
Read CLAUDE.md Section 7. Write engine/losses.py.

1. For every alert: energy_loss_kwh = sum of max(expected_kw − actual_kw, 0) × 0.25 during the alert (for DATA_GAP use expected energy as "unknown/at-risk energy" and label it separately — don't mix with confirmed loss).
2. money_loss_inr = energy_loss_kwh × TARIFF_INR_PER_KWH (configurable ASSUMPTION; document in reports/assumptions.md and leave a TODO for the team to cite a source).
3. Daily tables per plant and per inverter: actual kWh, expected kWh, performance ratio, loss kWh, loss ₹.
4. Totals: loss by fault type, by inverter (top 5 worst), by plant, over the whole period; and "projected annual loss if not fixed" (simple extrapolation, clearly labelled as estimate).
5. Add energy and ₹ loss to each alert in alerts.parquet; save daily tables to data/processed/; totals under "losses" in reports/metrics.json.

Explain simply how we turn "missing power" into rupees, and why it is an estimate.
```

**You check:** totals add up · the biggest loss source makes sense when you look at its alerts.

---

## Phase 7 — Validate the detector with injected faults (our PROOF) (owner: P3)

```
Read CLAUDE.md rule 3. Write engine/validate.py — we have no official fault labels, so we test the detector by creating faults ourselves.

1. Take the TEST days for inverters with NO existing alerts (healthy copies).
2. Inject synthetic faults with known start/end (seeded, reproducible):
   - trip: set ac to 0 for 1–4 hours at midday
   - underperformance: multiply ac by 0.6–0.85 for 2–6 hours
   - soiling: gradual decline of 0.3–1% per day over the test period
   - data gap: remove readings for 1–3 hours
3. Run the SAME detector (no threshold changes) on the injected data.
4. Measure per fault type: detection rate (recall), false alarms on untouched healthy data (precision), average detection delay, and loss-estimate error (estimated kWh vs true injected kWh).
5. Also test the threshold trade-off: re-run with 3 threshold settings and show more sensitive = more false alarms.
6. Save under "validation" in reports/metrics.json and data/processed/validation_*.parquet. Export a PNG chart of one injected fault being caught.

Be honest: report which faults are hard to catch (e.g. small underperformance) and why.
Explain simply what "precision" and "recall" mean using our alerts as the example.
```

**You check:** numbers are realistic (not all 100%) · P3 can explain recall vs false alarms.

---

## Phase 8 — The API (connects AI engine to website) (owner: P3)

```
Read CLAUDE.md Sections 3 (rule 4), 6. Write api/main.py with FastAPI. It reads precomputed files only (load once at startup) and serves the web/ folder as static files at "/".

Endpoints (JSON):
- GET /api/plants → list of plants with inverter counts and date range
- GET /api/overview?plant=&date= → KPI cards: actual kWh, expected kWh, performance ratio, loss kWh, loss ₹, active alerts by severity, one-line takeaway sentence
- GET /api/plant/timeseries?plant=&date= → 15-min actual vs expected (plant total) + irradiation
- GET /api/plant/heatmap?plant= → daily performance ratio per inverter (inverter × day grid)
- GET /api/inverter/{id}?date= → inverter time series (actual, expected, peer median, missing flags) + its alerts + daily PR history
- GET /api/alerts?plant=&severity=&type=&status= → alert list (sortable fields)
- GET /api/alerts/{id} → full alert detail incl. evidence time series for the "Why?" chart
- POST /api/alerts/{id}/status → set Acknowledged / Resolved (store in a small JSON file data/processed/alert_status.json)
- GET /api/losses?plant= → losses by fault type, top inverters, daily loss trend, projected annual loss
- GET /api/validation → injected-fault test results
- GET /api/assumptions → list of assumptions with values
- GET /api/health → {"status": "ok"}

Use pydantic response models, sensible defaults (latest date, Plant 1), friendly 404 errors, and CORS enabled for local testing.
Write tests in tests/test_api.py with FastAPI TestClient for every endpoint.

Run: uvicorn api.main:app --reload and show me how to open http://localhost:8000/docs to try the API.
Explain simply what an API is using a restaurant waiter analogy.
```

**You check:** `/docs` page works · every endpoint returns data · tests pass.

---

## Phase 9 — Web dashboard: layout and Overview page (owner: P4)

```
Read CLAUDE.md Sections 3 (rule 5) and 10. Build the website in web/ with plain HTML, CSS and vanilla JS + Chart.js from a CDN. No frameworks, no npm.

1. web/css/style.css — design system: CSS variables for colours (solar amber accent, green/amber/red status, neutral greys), cards, KPI tiles, tables, badges, buttons, top nav bar, responsive grid, light theme (optional dark toggle).
2. web/js/api.js — small fetch helper with loading and error handling ("Engine offline — run uvicorn api.main:app").
3. Shared top bar on every page: product name + logo (simple sun icon in SVG), links (Overview, Plant, Inverters, Alerts, Validation, About), plant selector, replay-date selector (remember choice in localStorage, wrapped in try/catch).
4. web/index.html (Overview):
   - Takeaway sentence from the API
   - KPI tiles: Today's actual kWh, Expected kWh, Performance ratio, Energy lost, ₹ lost, Open alerts (by severity)
   - Chart: actual vs expected for the selected day (with irradiation on a second axis)
   - "Needs attention" list: top 5 open alerts with severity badges and links
   - Loss by fault type (doughnut or bar)

Make it look like a real professional monitoring product. Test it in the browser via uvicorn and fix all console errors.
```

**You check:** open `http://localhost:8000` → Overview loads with real numbers · no errors in the browser console (F12).

---

## Phase 10 — Plant, Inverter and Alerts pages (owner: P4)

```
Read CLAUDE.md Section 10. Build:

1. web/plant.html — plant actual vs expected over the full period (daily bars + PR line); inverter health heatmap (inverter × day grid coloured by performance ratio, built with a CSS grid/table — click a cell → inverter page for that day); top 5 worst inverters by loss.
2. web/inverter.html?id=…&date=… — inverter selector; 15-min chart of actual vs expected vs peer median for the chosen day with alert periods shaded; daily PR trend with trend line; this inverter's alerts list.
3. web/alerts.html — alert table with filters (plant, severity, type, status), sorting by loss/time/severity, search; click a row → side panel/modal with: reason sentence, evidence chart (actual vs expected during the alert), key numbers, energy & ₹ loss, recommended action, buttons "Acknowledge" / "Resolve" (POST to API, update UI); "Export CSV" button.

All charts: insight titles, units, tooltips. Mobile-friendly. Fix all console errors.
Then give me a 2-minute demo click-path through these pages.
```

**You check:** you can go Overview → alert → evidence chart → Acknowledge in under 30 seconds.

---

## Phase 11 — Extras that impress judges (owner: P4 + P3)

Part A (recommended):
```
Read CLAUDE.md. Build web/validation.html — "How do we know it works?":
- Explanation in 3 simple sentences of the injected-fault test
- Detection rate and false alarms per fault type (bar chart), detection delay, loss-estimate error
- Threshold trade-off chart (sensitivity vs false alarms)
- One example chart of an injected fault being caught
And web/about.html: problem, how it works (simple architecture diagram in HTML/SVG: Sensors/Data → Cleaning → Expected-output AI model → Fault rules + peer comparison → Loss estimator → Alerts API → Dashboard), datasets and licences, assumptions (from /api/assumptions), limitations, team.
```

Part B (optional — replay "live" mode):
```
Add a "Live replay" toggle on the Overview page: it steps through the selected day in 15-minute ticks (one tick per second), updating the chart and KPI tiles, and pops up an alert toast when a fault starts — so the demo looks like real-time monitoring. Use only precomputed data from the API (add an endpoint if needed). Add pause/speed controls.
```

Part C (optional — free AI summaries):
```
Read CLAUDE.md rule 9. Write engine/summaries.py: template-based daily "O&M brief" per plant (biggest issue, loss, recommended actions, priority order). Optional: if Ollama is running locally with a small model, rephrase the computed facts (never add new numbers; 20s timeout); otherwise use the template. Pre-generate briefs for all dates into data/processed/briefs.json, add GET /api/brief?plant=&date=, and show it as a card on the Overview page. USE_LLM = False by default.
```

---

## Phase 12 — Optional: New Site Estimator (scalability story) (owner: P3)

```
Read CLAUDE.md Section 4 (NASA POWER). Write engine/site_estimator.py and an endpoint GET /api/site-estimate?lat=&lon=&capacity_kw= that:
- Fetches the last 12 months of daily irradiance and temperature from the NASA POWER API (no key) for that location, with a 10-second timeout and caching to disk.
- Estimates expected monthly energy using our physics baseline formula (state assumptions: performance factor, temperature coefficient).
- Returns monthly expected kWh and a note on uncertainty.
Add web/estimator.html: inputs (lat, lon, capacity kW; preset buttons for Delhi, Jaipur, Chennai) → monthly bar chart.
If the internet is unavailable, show a friendly message. Explain how this shows our engine can scale to any new plant in India.
```

---

## Phase 13 — One-command pipeline, tests, polish (everyone)

```
Read CLAUDE.md Section 11.
1. Write run_all.py: load → clean → expected_model → detect_faults → losses → validate → (summaries if enabled), with step timing and a final summary of key metrics.
2. Ask me, then delete data/processed, models and reports/metrics.json and run it from scratch.
3. Complete tests: cleaning, model outputs exist, every alert has a reason and loss, API endpoints, losses add up.
4. Run pytest; fix failures.
5. Review: unclear names, missing docstrings, files > 250 lines, hard-coded numbers that belong in config, JS console errors, mobile layout.
6. Cross-check every number on the website comes from the API / metrics.json. Fix anything that doesn't.
7. Update README.md (≤ 10 beginner steps: setup, download data, run_all, start server, open browser) and PROGRESS.md.
Give me a final checklist: what works, assumptions, known limitations.
```

**You check:** a second team member follows the README on their own laptop and it works.

---

## Phase 14 — Deploy for free + presentation pack (owner: P4 + everyone)

Deploy:
```
Help me deploy the app (FastAPI serving the web/ folder) for free, step by step for a beginner, choosing the simplest option that works: Render.com free web service or Hugging Face Spaces (Docker).
1. Make the processed data small enough to commit (no data/raw; keep only what the API needs).
2. Add the needed files (e.g. Dockerfile or render.yaml, start command uvicorn api.main:app --host 0.0.0.0 --port $PORT).
3. Walk me through creating GitHub/Render (or HF) accounts and deploying. Wait for me at each manual step.
4. Warn me about free-tier sleep/cold start and tell me to open the site 2 minutes before presenting. Keep the local version as backup.
```

Presentation:
```
Read CLAUDE.md, reports/metrics.json, reports/model_card.md, reports/assumptions.md, reports/data_quality.md.
Create presentation/ with:
1. key_numbers.md — every number we will say, with its source file. Add a section "external facts to cite" listing what we must find sources for (India solar capacity, dust/soiling losses, tariff) — do not invent them.
2. slide_outline.md — 9–10 slides: Problem (losses found too late) · Who suffers & cost · Our solution in one picture · How the AI works (expected output + peer comparison + fault rules) · Live demo screenshots · Proof (injected-fault validation) · Loss in ₹ · Scalability (any plant, any inverter count, NASA-powered site estimator, real-time streams) · Competitive advantage (vs basic monitoring/SCADA threshold alarms and vs notebook analyses: reasons + ₹ loss + validation) · Future roadmap.
3. demo_script.md — 2-minute click-path with what to say at each step, plus a backup plan (local server / screenshots).
4. judge_qa.md — 20 tough questions with honest answers from OUR results: dataset only 34 days, no GPS location, Plant 1 DC quirk, how expected output works, why Random Forest, accuracy meaning, how we validated without labels, false alarms, clouds vs faults, tariff source, scaling to 1,000 inverters, real-time data, cost, what AI built vs what we did, limitations.
5. explain_like_im_new.md — one page per team member role, very simple language.
6. Export the 6 best charts/screenshots list to presentation/figures/.
```

---

## Rescue prompts

**Lost / new session**
```
Read CLAUDE.md and PROGRESS.md. Tell me in 5 bullets where we are, what works, and the next step.
```

**Error**
```
I got this error: <paste full error>. Explain simply what went wrong, fix it, and tell me how to avoid it.
```

**Website broken**
```
The page <name> is not working. Check the browser console errors and API responses, find the cause, fix it, and explain simply.
```

**Too complex**
```
This is too complex for us to explain to judges. Simplify it, keep the same result, and explain the new version like I'm 18.
```

**Learning mode (each owner after each phase)**
```
Explain <file name> line by line in simple language. Then quiz me with 5 questions a judge might ask about it and check my answers.
```

**Too good to be true**
```
These results look too good. Check for test data used in training, wrong time split, or bugs in validation. Report honestly.
```
