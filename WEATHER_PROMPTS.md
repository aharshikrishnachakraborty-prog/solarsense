# WEATHER_PROMPTS.md — Add "Sky & Temperature Intelligence" to SolarSense

Goal: show HOW the weather (sky condition + temperature) shapes energy production, using ONLY the
Kaggle dataset we already have — and use it to make fault detection smarter.

Put this file in the `solarsense/` folder next to CLAUDE.md. Paste one phase at a time into Claude Code
(or type: `Read WEATHER_PROMPTS.md and do Phase W1`). Wait for the plan → reply "OK" → do "You check".

### The honest idea (read this first — judges WILL ask)
The dataset has NO cloud sensor. It has: IRRADIATION (sunlight strength), AMBIENT_TEMPERATURE (air),
MODULE_TEMPERATURE (panel). So we DERIVE the sky condition from sunlight:
- **Clear-sky reference:** for every 15-minute time of day, the highest sunlight seen across all 34 days
  (smoothed) = "what a clear sky gives at this time".
- **Clear-sky index (CSI):** actual sunlight ÷ clear-sky reference. ~1.0 = clear sky, ~0.5 = cloudy, <0.3 = overcast.
- **Variability:** how fast sunlight jumps up and down → broken / passing clouds.
- **Temperature effect:** hot panels make less power. We measure HOW MUCH from our own data
  (temperature coefficient, %/°C) and compare with the typical range for silicon panels.

Pitch line: *"We don't have a cloud camera — we read the sky from the sunlight itself, and we measure
exactly how much power clouds and heat cost each day."*

Suggested owner: P2 (W1–W3), P3 (W4), P4 (W5–W6). ~2 days.

---

## Phase W1 — Sky condition from sunlight (owner: P2)

```
Read CLAUDE.md, PROGRESS.md and WEATHER_PROMPTS.md (intro). Do NOT break anything that already works.

Create engine/weather.py:
1. Clear-sky reference per plant: for each 15-minute time-of-day slot, take a high percentile (e.g. 95th–98th, in config) of IRRADIATION across all days, then smooth it across the day (rolling window) so it forms a clean bell curve. Explain the method in a comment and mark it as an ASSUMPTION in reports/assumptions.md (it is data-derived, not a physical model, because the plant's GPS location is not in the dataset).
2. For every daylight timestamp: clear_sky_irr, clear_sky_index = irradiation / clear_sky_irr (clip 0–1.2), and variability = rolling std of the change in clear_sky_index over ~1 hour.
3. Sky label per 15-min (thresholds in engine/config.py with comments):
   - Clear (CSI ≥ 0.8, low variability)
   - Partly cloudy (0.5–0.8, or variable)
   - Cloudy (0.3–0.5)
   - Overcast (< 0.3)
4. Daily sky summary per plant: average CSI, % time in each label, dominant label, "sunshine score" 0–100, and a plain-English sentence (e.g. "Mostly clear morning, clouds after 2 PM — 18% less sunlight than a clear day").
5. Save to data/processed/weather_15min.parquet and weather_daily.parquet; stats under "weather" in reports/metrics.json (number of clear/partly/cloudy/overcast days per plant).
6. Sanity checks: CSI ≈ 1 on the sunniest days; labels change smoothly, not randomly. Export a PNG of one clear day vs one cloudy day with the clear-sky curve.

Explain simply how we "see" clouds without a cloud sensor.
```
**You check:** pick the sunniest and the cloudiest day — do the labels match what the chart looks like?

---

## Phase W2 — Temperature effect on power (owner: P2)

```
Read CLAUDE.md and WEATHER_PROMPTS.md. Extend engine/weather.py:

1. Temperature coefficient from OUR data: using healthy daylight rows (no alerts) with good sunlight, compute efficiency = ac_kw / irradiation (per inverter, normalised) and fit a simple linear relation against module_temp. Report the coefficient in %/°C with a confidence range and compare it with the typical crystalline-silicon range (about −0.3 to −0.5 %/°C) — say honestly whether ours is close or not and why.
2. Heat derating per 15-min: estimated power lost because the panel was hotter than 25 °C = expected_kw × |coef| × max(module_temp − 25, 0). Daily heat loss in kWh and ₹ (tariff from config).
3. Panel heating: module_temp − ambient_temp; how it grows with sunlight (simple fit). Flag "hot hours" (thresholds in config).
4. Daily temperature summary: min/max ambient, max module temp, hours above threshold, heat loss kWh/₹, plain-English sentence (e.g. "Panels reached 61 °C at 1 PM — heat cost about 4% of today's energy").
5. Add to weather_15min/weather_daily parquet; metrics under "temperature" in reports/metrics.json; export a PNG scatter (module temp vs efficiency with fitted line).

Explain simply why hot panels make less electricity, and what our coefficient means.
```
**You check:** coefficient is negative and in a believable range · P2 can explain it with one example.

---

## Phase W3 — Energy waterfall: where did the energy go? (owner: P2)

```
Read CLAUDE.md and WEATHER_PROMPTS.md. Create engine/energy_breakdown.py.

For each plant and day, split energy into a "waterfall" that adds up exactly:
1. Clear-sky potential (kWh) — what the plant would make on a clear sky at 25 °C (use our expected-output model / physics baseline fed with clear_sky_irr and module_temp = 25; explain the method).
2 − Cloud / weather loss — potential minus what the actual sunlight allowed.
3 − Heat loss — from Phase W2.
4 − Fault loss — from our existing alerts/losses (do not double-count; explain the order of subtraction).
5 − Other / unexplained (residual, can be ±).
6 = Actual energy.

Check: the parts must sum to actual within rounding — add a test. Label clearly: weather losses are NATURAL (nobody can fix clouds), fault losses are FIXABLE (this is where money is saved). Save to data/processed/energy_breakdown.parquet and totals under "breakdown" in reports/metrics.json.

Explain simply the difference between natural losses and fixable losses — this is a key pitch point.
```
**You check:** pick 2 days — the numbers add up; a cloudy day shows a big weather loss, a fault day a big fault loss.

---

## Phase W4 — Weather-aware fault detection (owner: P3)

```
Read CLAUDE.md and WEATHER_PROMPTS.md. Improve engine/detect_faults.py using the sky labels — without lowering detection of real faults:

1. Underperformance alerts during Overcast or highly variable sky: require stronger evidence (peer comparison must also fail) or lower the confidence, because low sunlight makes % deviations noisy. Thresholds in config.
2. Add to every alert: sky_condition and module_temp during the alert, and a sentence like "Sky was clear (CSI 0.92), so low output is NOT caused by clouds" or "Partly cloudy — confirmed by comparison with neighbouring inverters".
3. Add an alert confidence (High/Medium/Low) based on sky condition + peer evidence.
4. Re-run validation (engine/validate.py) BEFORE and AFTER this change, also injecting faults on cloudy days. Report detection rate and false alarms for both versions in reports/metrics.json under "validation_weather". Keep the change only if false alarms drop without losing real detections — report honestly either way.
5. Update reports/model_card.md.

Explain simply how knowing the weather avoids blaming the inverter for a cloud.
```
**You check:** before/after numbers exist · alert reasons now mention the sky.

---

## Phase W5 — API + "Weather & Energy" page (owner: P4)

```
Read CLAUDE.md Section 10 and WEATHER_PROMPTS.md.

API (api/main.py) — read precomputed files only:
- GET /api/weather/day?plant=&date= → 15-min irradiation, clear-sky curve, CSI, sky label, ambient & module temp, actual & expected kW, heat loss; daily summary sentences.
- GET /api/weather/calendar?plant= → per day: dominant sky, sunshine score, max module temp, actual kWh, breakdown totals.
- GET /api/weather/temperature?plant= → scatter data (module temp vs efficiency), fitted line, coefficient.
- GET /api/breakdown?plant=&date= → waterfall parts for a day (or whole period if no date).
Add tests for each endpoint.

New page web/weather.html ("Weather & Energy") + nav link:
1. Takeaway sentence (e.g. "17 Jun: partly cloudy afternoon cost 2,100 kWh; heat cost 900 kWh; faults cost 300 kWh").
2. Sky strip: a coloured band across the day (☀️ clear / ⛅ partly / ☁️ cloudy / 🌫 overcast) aligned above the chart.
3. Main chart: actual sunlight vs clear-sky curve (shaded gap = clouds) + actual vs expected power.
4. Temperature chart: ambient vs module temperature through the day, hot hours shaded, heat-loss kWh shown.
5. Energy waterfall chart for the day (Chart.js bar chart with floating bars): Clear-sky potential → − clouds → − heat → − faults → − other → Actual. Natural losses in grey/blue, fixable faults in red.
6. Weather calendar: a grid of all 34 days, each tile showing sky icon, sunshine score, max panel temp and kWh; click a tile → that day.
7. Temperature insight card: scatter of panel temperature vs efficiency with fitted line and "Every +1 °C costs ~X% power" (from the API).
All charts have insight titles, units, tooltips; ⓘ notes explain the clear-sky method is data-derived. Mobile-friendly. Fix all console errors.
```
**You check:** open the page · click a cloudy day and a clear day in the calendar — the story is obvious in 10 seconds.

---

## Phase W6 — Weave weather into existing pages + pitch (owner: P4 + everyone)

```
Read CLAUDE.md and WEATHER_PROMPTS.md.

1. Overview page: add a weather mini-card (sky icon, sunshine score, max panel temp, "Weather cost X kWh, faults cost Y kWh") and draw the sky strip above the main chart.
2. Inverter page and alert "Why?" panel: show the sky condition and module temperature during the alert, with the new reason sentence.
3. Live replay (if built): update the sky icon and temperature each tick.
4. Action Plan / Advisor (if built): only fixable losses drive actions; weather losses are shown as context ("no action needed").
5. Update presentation/: add 1 slide "Weather intelligence — natural vs fixable losses" with the waterfall, add these judge questions with honest answers to judge_qa.md:
   - "Your data has no cloud sensor — how do you know it's cloudy?"
   - "How accurate is your clear-sky reference with only 34 days and no GPS?"
   - "Is your temperature coefficient realistic?"
   - "Couldn't a fault be hidden by a cloudy day?"
   - "Why does weather matter to an operator if they can't control it?"
6. Run run_all.py (add the new steps in order: … expected_model → weather → detect_faults → losses → energy_breakdown → validate …), pytest, and test every page. Update README and PROGRESS.md.

Give me a 30-second demo script for the Weather & Energy page.
```
**You check:** `python run_all.py` → `pytest` → website: every page works, numbers add up.

---

## Rescue prompts
- Numbers don't add up: `The energy waterfall doesn't sum to actual for <date>. Find why, fix it, explain simply.`
- Labels look wrong: `Day <date> looks sunny on the chart but is labelled Cloudy. Check the clear-sky reference and thresholds and fix it.`
- Too complex: `This weather part is too complex to explain to judges. Simplify it, keep the same result, explain like I'm 18.`
