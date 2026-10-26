# Explain it like I'm new — one page per team role

Read your own page until you can say it without looking. Numbers are in `key_numbers.md`.

---

## P1 — Data & Problem (Phases 1–2)

**The problem in one sentence:** solar plants lose energy when an inverter breaks or gets weak, and people
usually notice too late.

**The data:** two solar plants in India, 22 **inverters** each, a reading every 15 minutes for 34 days.
- An **inverter** is the box that turns the panels' electricity (DC, like a battery) into grid electricity
  (AC, like a wall socket).
- **Irradiation** = how strong the sunlight is. 0 at night, about 1 at a sunny noon.
- **DAILY_YIELD** = energy made so far today. We found it unreliable, so we calculate energy ourselves:
  power × 0.25 hours.

**What we fixed:**
- Plant 1's DC numbers were ~10× too big (physically impossible) → divided by a factor we computed, labelled ASSUMPTION.
- Missing readings are **kept as visible gaps**, never filled with made-up values — because a silent inverter
  might be a broken one.

**If a judge asks "is your data clean?":** "We checked every column, found 3 big problems (Plant 1 DC, missing
readings, broken energy counters), and documented how we handled each in `reports/data_quality.md`."

---

## P2 — AI Model & Fault Detection (Phases 3–5)

**Expected output:** our AI learns how much power an inverter *should* make for the sunlight and temperature.
It learned from the first 24 days and was tested on the last 10 days it had never seen (that's fair testing).

**Random Forest in one breath:** 100 small decision flowcharts each make a guess; we average them.

**R²:** how much of the ups and downs the model explains. Plant 1: 0.96 = 96%.

**Peer comparison:** compare each inverter with its 21 neighbours at the same moment. If everyone dips, it's a
cloud. If only one dips, it's a fault.

**Fault rules (examples):**
- **Trip:** strong sun but ~0 output for at least 30 minutes.
- **Underperformance:** at least 20% below expected *and* below neighbours for at least 1 hour.
- **Data gap:** no readings during daylight for at least 30 minutes.

**Isolation Forest (optional):** "finds the odd ones out" — only a hint, never an alert, because it can't say *why*.

**If a judge asks "why not let AI decide everything?":** "Operators need a reason and an action. Rules give
both; the AI gives the expected value the rules compare against."

---

## P3 — Losses, Validation & API (Phases 6–8)

**Turning missing power into rupees:** every 15 minutes, (expected − actual) kW × 0.25 h = kWh lost.
Add them up for the alert, then × tariff (₹/kWh). The tariff is an assumed value until we cite a source.

**Lost vs at risk:** a trip is **lost** energy (we saw 0 output). A data gap is **at risk** (we can't see what
happened) — we never mix them.

**Validation (our proof):** we broke healthy data on purpose and checked the detector found it.
- **Recall** = of the faults we planted, how many it caught. (Trips: 100%.)
- **Precision** = of the alarms it raised, how many were real.
- More sensitive settings catch more but cry wolf more — we showed that trade-off.

**The API = the waiter:** the website (customer) orders "overview for Plant 2 on 27 May"; the API (waiter)
brings the pre-cooked answer from the pipeline's files (kitchen) as JSON.

---

## P4 — Web Dashboard & Pitch (Phases 9–14)

**What the website does:** shows results — it never calculates them. Every number comes from the API.

**The pages:**
- **Overview** — today's summary, the actual-vs-expected chart, what needs attention, and the live replay.
- **Plant** — the health map: every inverter on every day, red = problem.
- **Inverters** — one inverter's day with alert periods shaded red.
- **Alerts** — the work list: filter, see "Why?", Acknowledge, Resolve, export to Excel.
- **Validation** — the proof it works, including what it misses.
- **About** — how it works, data sources, assumptions, limitations.

**Live replay:** plays a recorded day back in 15-minute steps so it *looks* like live monitoring. Always call it
a **replay** on stage — it is real recorded data, not a live feed.

**If a judge asks "is this a mock-up?":** "No — change the plant or date and every number reloads from the
engine. If you stop the engine, the site says so."

---

## Everyone — the weather part (WEATHER_PROMPTS.md, W1–W6)

**Reading the sky without a cloud sensor (P2):** for each time of day, the brightest sunlight seen over the 34 days
= "clear sky". Actual ÷ clear sky = **clear-sky index**: ~1 clear, ~0.5 cloudy, < 0.3 overcast. Sunlight that
jumps up and down = passing clouds.

**Heat (P2):** panels are rated at 25 °C. Hotter panels make less power — we measured about **0.4% less per °C**
(Plant 1). At 60 °C that is 35 × 0.39 ≈ 14% less than a cool panel in the same sun.

**The waterfall (P2):** clear-sky potential − clouds − heat − faults − not measured − other = actual. The parts
always add up (a test checks it). Clouds and heat are **natural**; faults are **fixable** — that is the pitch.

**Weather-aware alerts (P3):** every alert shows the sky, panel temperature and a confidence level. We tested a
stricter rule for cloudy skies; it lost real faults, so we switched it off and said so.

**The page (P4):** Weather & Energy — sky band, sunlight vs clear-sky chart, temperature chart, waterfall,
calendar of all days, and "every +1 °C costs ~X% power".

