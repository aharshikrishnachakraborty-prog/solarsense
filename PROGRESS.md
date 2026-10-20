# PROGRESS.md — SolarSense build tracker

Tick a box (`[x]`) when the phase's "You check" list in PROMPTS.md passes.

| Owner | Role |
|---|---|
| P1 | Data & Problem (Phases 1–2) |
| P2 | AI Model & Fault Detection (Phases 3–5) |
| P3 | Losses, Validation & API (Phases 6–8) |
| P4 | Web Dashboard & Pitch (Phases 9–14) |

## Checklist

- [x] **Phase 0** — Setup: venv, folders, requirements, config (everyone)
- [x] **Phase 1** — Load and understand the data (P1)
- [x] **Phase 2** — Clean and merge (P1)
- [x] **Phase 3** — Expected-output model (AI core) (P2)
- [x] **Phase 4** — Fault detection with reasons (P2)
- [x] **Phase 5** — Optional extra AI check: Isolation Forest (P2)
- [x] **Phase 6** — Energy and money loss (P3)
- [x] **Phase 7** — Validate the detector with injected faults (P3)
- [x] **Phase 8** — The API (P3)
- [x] **Phase 9** — Web dashboard: layout and Overview page (P4)
- [x] **Phase 10** — Plant, Inverter and Alerts pages (P4)
- [x] **Phase 11** — Extras: A validation + about · B live replay (opt.) · C AI summaries (opt.) (P4 + P3) — A+B done, C skipped
- [ ] **Phase 12** — Optional: New Site Estimator (P3)
- [x] **Phase 13** — One-command pipeline, tests, polish (everyone)
- [ ] **Phase 14** — Deploy for free + presentation pack (P4 + everyone)

## Log

### Phase 0 — Setup (2026-10-20)
- Python 3.12.11 used for `.venv` (laptop default is 3.14, which is too new).
- Libraries installed and pinned in `requirements.txt`.
- Folder structure from CLAUDE.md Section 6 created (empty placeholder files).
- `engine/config.py` created: paths, `RANDOM_SEED = 42`, `INTERVAL_HOURS = 0.25`, tariff placeholder (ASSUMPTION).
- All 4 Kaggle CSVs present in `data/raw/`.
- **Open TODO:** find a source for the tariff value (₹/kWh).

### Phase 1 — Load and understand the data (2026-10-20)
- `engine/load_data.py`: loads the 4 CSVs, exact date format per file (`DATE_FORMATS` in config).
- `engine/explore_data.py` (run: `python -m engine.explore_data`) → `reports/data_quality.md` + `"data"` in metrics.json.
- Helpers: `engine/metrics.py` (merge sections into metrics.json), `engine/report_data_quality.py` (writes the report).
- Config additions: `PLANTS`, `READINGS_PER_DAY`, `DAYLIGHT_IRRADIATION_THRESHOLD = 0.02`, `NIGHT_HOURS`.
- Findings: Plant 1 DC is ~10× too large (confirmed); 4 Plant 2 inverters miss ~28% of daylight readings;
  DAILY_YIELD and Plant 2 TOTAL_YIELD counters are unreliable → we compute energy from AC_POWER × 0.25 h.
- **Note for Phase 2:** Plant 1 weather sensor misses 82 timestamps — those slots have no sunlight value.

### Phase 2 — Clean and merge (2026-10-20)
- `engine/clean_data.py` (run: `python -m engine.clean_data`) → `data/processed/clean.parquet`, 143,616 rows
  (2 plants × 22 inverters × 3,264 slots). Missing readings are explicit rows (`is_missing`, power blank).
- Plant 1 DC divided by **10.001** (computed from data; ASSUMPTION) → AC/DC now 0.9787 for both plants.
- `engine/assumptions.py` keeps the assumptions list (metrics.json `"assumptions"` + `reports/assumptions.md`).
- `tests/test_clean.py`: 7 tests, all pass. Stats under `"cleaning"` in metrics.json.
- matplotlib 3.11.2 approved and installed (for Phase 3 charts).

### Phase 3 — Expected-output model (2026-10-20)
- `engine/expected_model.py` (run: `python -m engine.expected_model`, ~25 s) → `data/processed/expected.parquet`
  (every daylight row: expected_kw, residual_kw, residual_pct, peer_ratio, peer_median_kw, split train/test).
- `engine/model_report.py` → `reports/model_card.md` + 2 PNGs in `reports/figures/`. Metrics under `"expected_model"`.
- Time split: train 15 May–7 Jun (24 days), test 8–17 Jun (10 days). Random Forest chosen for both plants.
- Test results (RF): Plant 1 R² 0.960 (0.976 without outages); Plant 2 R² 0.121 (0.839 without outages).
- **Finding for Phase 4:** Plant 2 has frequent outages (9.0% of test readings: strong sun, ~0 output), often
  30–60% of inverters at once. The low "all rows" R² comes from these real problems, not a broken model.
- **Known limitation:** Plant 2 model is weaker on healthy rows too (MAPE 15.5% vs 5.7% for Plant 1).

### Phase 4 — Fault detection with reasons (2026-10-20)
- `engine/detect_faults.py` (run: `python -m engine.detect_faults`) → `data/processed/alerts.parquet`;
  `engine/alert_text.py` writes reasons, severity, actions. All thresholds in `engine/config.py` (Phase 4 block).
- **429 alerts:** 358 INVERTER_TRIP, 50 DATA_GAP, 16 UNDERPERFORMANCE, 5 SENSOR_ISSUE; 0 DEGRADATION, 0 OVERHEATING.
  Severity: 203 Critical, 141 High, 79 Medium, 6 Low. Counts under `"alerts"` in metrics.json.
- Plant 2 trips are a recurring pattern (~10 per day, mostly starting 09:00–11:00; median inverter trips on 14.5 of 34 days).
- No degradation found: steepest trend −0.24%/day is within Plant 2's normal noise (−0.24 to +0.33%/day);
  threshold kept at −0.3%/day — Phase 7 will measure what it can catch.
- Overheating is plant-level only (one temperature sensor per plant); none found.
- Data gaps capped at "High" severity (no confirmed loss). Trip takes priority over underperformance.
- `tests/test_detect.py`: 7 tests; total 14 pass.
- **For Phase 6:** `energy_loss_kwh` / `energy_at_risk_kwh` already computed per alert (needed for severity) — add ₹ there.

### Phase 5 — Optional "unusual day" score (2026-10-20)
- `engine/anomaly_score.py` (run: `python -m engine.anomaly_score`) → `data/processed/anomaly_days.parquet`,
  `"anomaly_score"` in metrics.json. Separate file because detect_faults.py is near the 250-line limit.
- Isolation Forest per plant on 8 daily features; contamination 5% (ASSUMPTION, in assumptions.md).
- 76 of 1,496 inverter-days flagged; 50 (65.8%) already have a rule alert; 26 are new (25 in Plant 1).
- Verdict: **small value**. Plant 2 flags repeat the rules (37 of 38). Real find: Plant 1 `bvBOhCH3iADSZry`
  flagged on 9 days, ~5.5% below peers all period (median peer ratio 0.945) — too mild for the 20% rule.
  Rest is mostly noise (e.g. 17 Jun: single missing/dipping readings on an otherwise normal day).
- Decision for UI: optional quiet hint only (Inverter page), never on Overview / alert list.

### Phase 6 — Energy and money loss (2026-10-20)
- `engine/losses.py` (run: `python -m engine.losses`) → ₹ columns in alerts.parquet,
  `data/processed/daily_plant.parquet`, `daily_inverter.parquet`, `"losses"` in metrics.json.
- Confirmed fault loss **927,680 kWh** (₹27.8 lakh at placeholder ₹3/kWh); at risk (data gaps) 380,157 kWh — kept separate.
- Plant 2 = 913,398 kWh of it (99% from trips); matches Plant 2 net shortfall 922,114 kWh → alerts explain ~99%.
- Projected annual (ESTIMATE, in assumptions.md): 9,958,920 kWh ≈ ₹2.99 crore at placeholder tariff.
- `tests/test_losses.py`: 5 tests; total 19 pass.
- **Still open:** cite a real tariff source (TODO in config + assumptions.md).

### Phase 7 — Validation with injected faults (2026-10-20)
- `engine/validate.py` (run: `python -m engine.validate`, ~70 s) + helpers `engine/fault_injection.py`,
  chart `engine/validate_report.py`. Outputs: `"validation"` in metrics.json, `validation_injections.parquet`,
  `validation_tradeoff.parquet`, `reports/figures/validation_injected_fault_caught.png`.
- Deviation (approved): "healthy" = clean inverter-days (no alert), because Plant 2 has no alert-free inverter.
  Soiling tested on Plant 1 only (needs inverters healthy all 10 test days).
- Refactor: `add_residuals()` (expected_model) and `detect_inverter_events()` (detect_faults) so validation runs
  the exact same code. Re-ran pipeline: model metrics, alert counts and losses unchanged.
- Recall: trip 100% (95), data gap 100% (95), underperformance 71.6% (95; only 5.6% when output kept ≥ 80%),
  soiling 80% (20; 0% of 2 below 0.5%/day). Soiling precision 44.4% (2 Plant 2 inverters trend down in 10-day window).
- Trade-off: sensitive → underperformance recall 98.9% but 59 false alarms; strict → 24.2%, 0 false alarms.
- Caveat: default false alarms ≈ 0 by construction (healthy = days default detector was silent).
- `tests/test_validate.py`: 4 tests; total 23 pass.

### Phase 8 — The API (2026-10-20)
- `api/main.py` (run: `uvicorn api.main:app --reload`) + `api/data_store.py` (loads files once),
  `api/schemas.py` (pydantic), `api/routes/plants.py`, `alerts.py`, `reports.py`. Serves `web/` at `/`.
- All 12 endpoints from PROMPTS.md work; defaults Plant 1 + latest date (2020-06-17); friendly 404s;
  CORS on; NaN → null. Alert status saved in `data/processed/alert_status.json` (created on first change).
- Alert list `status=Active` = Open + Acknowledged; `sort=loss|time|severity`.
- `tests/test_api.py`: 17 tests (status test uses a temp file); total 40 pass.
- Known warning: Starlette suggests `httpx2` for TestClient — harmless; not installed (new library → ask first).

### Phase 9 — Web dashboard: layout + Overview (2026-10-20)
- `web/css/style.css` (design system, light + dark), `web/js/api.js` (fetch + formatting + errors),
  `web/js/layout.js` (shared top bar, plant/date/theme remembered in localStorage with try/catch),
  `web/js/charts.js` (Chart.js 4.4.1 from jsDelivr CDN), `web/index.html` + `web/js/overview.js`.
- Overview: takeaway, 6 KPI tiles (₹ tile has ⓘ tariff ASSUMPTION), actual vs expected + irradiation chart,
  "Needs attention" (top 5 open alerts on the chosen day), loss by fault type (whole period).
- API: added optional `date=` filter to `/api/alerts` (+1 test; total 41 pass).
- Other pages are placeholders with the top bar (built in Phases 10–11).
- Tested in headless Chrome (laptop 1366×768, phone 390×844, dark theme, API offline): no console errors,
  no sideways scroll on phone, offline banner works. Fixed: phone overflow, missing favicon, dark-mode link colours.

### Phase 10 — Plant, Inverter and Alerts pages (2026-10-20)
- `web/plant.html` + `js/plant.js`: 34-day actual vs expected bars + PR line, inverter × day heatmap
  (click → inverter page), top 5 inverters by loss.
- `web/inverter.html` + `js/inverter.js`: inverter picker, 15-min actual vs expected vs peer median with alert
  periods shaded, daily PR + trend line + "unusual day" dots, this inverter's alerts.
- `web/alerts.html` + `js/alerts.js` + `js/alert_panel.js`: filters, search, sort, 50 rows + "Show more",
  CSV export, side panel (reason, "Why?" chart, key numbers, loss, action, Acknowledge/Resolve/Re-open),
  deep links `alerts.html?id=…`.
- API: added `GET /api/plant/daily` and `pr_trend` in `/api/inverter/{id}` (+2 tests; total 42 pass).
- Shared: `prStatus()` colour bands and `alertOverlapsDay()` in api.js; `Charts.shade()` in charts.js.
- Browser-tested (laptop + phone): no console errors, no page sideways scroll. Acknowledge click-path works;
  the test alert (P2-TRIP-0090) was set back to Open afterwards.
- Note: Alerts-page ₹ total sums per-alert rounded rupees (₹27,83,028), so it can differ by a few ₹ from the
  metrics total (₹27,83,041).

### Phase 11 — Validation, About, Live replay (2026-10-20) — parts A + B (C skipped: Ollama not installed)
- `web/validation.html` + `js/validation.js`: 3-sentence method, recall + false alarms per fault type,
  "what we miss" (underperformance by size), results table, threshold trade-off, caveats, example PNG.
- `web/about.html` + `js/about.js`: problem, SVG architecture diagram, sources & licences, limitations,
  live assumptions table, team section. **TODO(team): names, Kaggle dataset licence.**
- Live replay on Overview (`js/replay.js`): ▶ Live replay, pause/resume, 1×/2×/4×, stop; toasts when alerts start.
  Running totals come from new `GET /api/replay` (last tick = day totals, tested).
- API: `/figures` serves `reports/figures/` read-only. Tests: +2 (total 44 pass).
- Browser-tested laptop + phone: no console errors, no page sideways scroll; replay advances and toasts appear.

### Website fixes after Phase 11 (2026-10-20)
- "Performance ratio" → **"Actual vs expected"** in all visible text (6 pages, API takeaways, /docs field titles),
  with ⓘ "Above 100% means the plant produced more than our model estimated." Internal field name
  `performance_ratio` kept on purpose (pipeline files unchanged).
- Plant-wide SENSOR_ISSUE alerts with 0 kWh are **data-quality notices**: excluded from "Needs attention",
  the open-alert count and replay counts; shown as a banner on Overview linking to About. Still listed on Alerts page.
  API: `data_quality_notices` in `/api/overview`, `include_notices=false` on `/api/alerts`.
- Default replay date = plant's **highest-loss day** (Plant 1: 07 Jun, Plant 2: 27 May). `/api/plants` returns
  `worst_loss_date`; plant endpoints default to it. Date choice now kept per browser session only.
- Tariff label → "(assumed tariff — see About)"; still configurable (`TARIFF_INR_PER_KWH`). assumptions.md lists it
  with **TODO(team): cite our source**. Loss totals unchanged.
- Takeaway numbers now use Indian grouping + round .5 up, matching the tiles. Fixed phone overflow from longer date label.
- Tests: 47 pass. All 6 pages browser-tested at laptop + phone: no console errors, no sideways scroll.

### Phase 13 — One-command pipeline, tests, polish (2026-10-20)
- `run_all.py`: `python run_all.py` rebuilds everything from the raw CSVs in ~97 s (7 timed steps + summary);
  `--skip-validation` for a quick rebuild. Friendly stop if raw data is missing or a step fails.
- **Rebuilt from scratch:** data/processed, models and metrics.json were moved to a backup (not deleted) and
  rebuilt. Result: every number in metrics.json identical (only the new `fault_sizes` entry added); 6 of 8
  processed files identical cell-by-cell; the other 2 differ by ≤ 1.1e-12 kW (Random Forest float rounding) —
  no alert, flag or reported number changed. Reproducible with seed 42.
- Tests: +`tests/test_model.py` (outputs exist, no negative/blank expected, time split, R² not suspicious),
  +every alert has a reason and loss, +`/api/settings` test, docstrings on all tests → **53 pass**.
- Review: validation fault sizes + scatter sample moved to config; no file > 250 lines; every function has a
  docstring; placeholders `summaries.py` / `site_estimator.py` say "not built".
- Numbers on the website: removed typed-in thresholds ("85%", "20%", "80–85%", "Top 5", plant list) — they now come
  from code constants or the API (`GET /api/settings`, `fault_sizes` in /api/validation).
- README rewritten: 10-step beginner setup + pages, how it works, troubleshooting.
- Browser-tested all 6 pages (laptop + phone): no console errors, no sideways scroll.

### Phase 14 — Deploy + presentation pack (2026-10-20) — IN PROGRESS (waiting for Render account steps)
- `presentation/`: `key_numbers.md` (generated by `python presentation/make_key_numbers.py` from metrics.json —
  every number with its source, plus "External facts to cite" TODO list), `slide_outline.md` (10 slides),
  `demo_script.md` (2-min click-path + backup plan), `judge_qa.md` (20 honest answers),
  `explain_like_im_new.md` (one page per role), `figures/` (6 dashboard screenshots + README).
- Deploy files: `requirements-deploy.txt` (website-only libraries), `render.yaml` (Render Blueprint, free plan,
  Python 3.12.11, start `uvicorn api.main:app --host 0.0.0.0 --port $PORT`, health check `/api/health`).
- Rehearsal in a fresh venv with only the deploy requirements: all endpoints + pages + figures OK
  (~0.2–0.4 s each), memory 147 MB (peak 161 MB) — fits Render free (512 MB).
- **GitHub Pages copy (requested):** https://ojasguptaa.github.io/solarsense/ — static export
  `python -m api.export_static` (2,208 saved API answers, 35.8 MB) + `web/js/mode.js` static switch +
  `.github/workflows/pages.yml` (builds and publishes on every push). Tested locally under /solarsense/ with a
  plain file server: all 6 pages, plant switch, alert panel, Acknowledge (saved in browser), live replay,
  figures — no console errors, laptop + phone. Repo to be made public by the team (Pages needs it on a free plan).
- Removed a stray "ma" line accidentally committed in PROMPTS.md. Tests: 54 pass.
