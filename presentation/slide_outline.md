# Slide outline — SolarSense (11 slides, ~5½ minutes + 2-minute demo)

Every number below is in `key_numbers.md` with its source. ₹ values: always say **"at an assumed tariff"**.
Items marked **[CITE]** need an external source first (see "External facts to cite" in `key_numbers.md`) —
drop the line if the team cannot find one.

---

## 1. The problem: losses are found too late
- Solar operators often learn that an inverter is down or weak **only after the losses pile up** (end-of-month yield).
- One inverter trip at midday can silently cost hours of generation.
- **Visual:** a calendar with "found on day 30" vs "found in 30 minutes".
- *Say:* "By the time someone notices, the energy is already gone."

## 2. Who suffers, and what it costs
- Plant operators and O&M engineers; owners lose revenue.
- In our data alone: **9,27,680 kWh lost to detected faults in 34 days** (≈ ₹27,83,041 at an assumed ₹3/kWh).
- Plant 2 produced only **82%** of what the weather allowed.
- [CITE] India's solar capacity — to show how big this is nationally.

## 3. Our solution in one picture
- **Visual:** `figures/6_how_it_works_diagram.png`
- Data → cleaning → **expected-output AI** → fault rules + peer comparison → loss in kWh and ₹ → alerts → dashboard.
- *Say:* "We compare what every inverter **made** with what it **should** have made for the weather."

## 4. How the AI works
- **Expected output:** Random Forest trained on the first 24 days, tested on the last 10 days it never saw.
  - Plant 1: R² **0.96** on test days; on healthy rows a simple physics formula scores the same (0.9764 vs 0.9758) — sunlight drives ~99% of the model's decisions.
- **Peer comparison:** each inverter vs its 21 neighbours under the same sky → clouds don't cause false alarms.
- **Fault rules with reasons:** trip, underperformance, data gap, slow degradation, overheating, sensor issues.
- The AI never decides alone — every alert comes from a clear rule and says *why*.

## 5. Live demo (screenshots as backup)
- **Visuals:** `figures/1_overview_plant2_worst_day.png`, `figures/2_alert_why_panel.png`, `figures/4_inverter_alert_shaded.png`
- Follow `demo_script.md` (2 minutes).

## 6. Proof: does it really catch faults?
- No official fault labels exist → we **planted 305 faults** in healthy data and ran the same detector.
- Trips **100%** caught (≈32 min), data gaps **100%**, underperformance **71.6%**, slow soiling **80%**.
- **Honest:** small dips (output still ≥ 80%) caught only **5.6%** — by design, to avoid false alarms.
- **Visual:** `figures/5_validation_proof.png`

## 7. The money: loss in ₹
- **429 alerts**, **99%** of lost energy caused by **inverter trips**.
- Worst inverter: **Plant 2, LYwnQax7tkwH5Cb — 80,807 kWh lost, 24 alerts**.
- If nothing is fixed: **≈ 99,58,920 kWh per year** (≈ ₹2.99 crore at the assumed tariff) — clearly an **estimate**.
- Data gaps are shown separately as **"at risk" (3,80,157 kWh)** — not counted as lost.

## 8. Weather intelligence — natural vs fixable losses
- We have **no cloud sensor**: we **read the sky from the sunlight itself** (a clear-sky curve learned from the
  brightest days at each time of day). Plant 2: **10 clear, 20 partly cloudy, 3 cloudy, 1 overcast** days.
- Hot panels make less power: we **measured −0.39% per °C** on Plant 1 (silicon datasheets: −0.3 to −0.5).
- **Visual:** the energy waterfall on the **Weather & Energy** page (`figures/7_weather_energy_waterfall.png`):
  clear-sky potential → − clouds → − heat → − **faults (red)** → − not measured → actual.
- Both plants, 34 days: **52,59,927 kWh natural** (clouds + heat — nobody can fix them) vs
  **9,27,680 kWh fixable** (faults — where money is saved).
- Every alert now says what the sky was: *"Sky was clear (clear-sky index 0.98), so low output is NOT caused by clouds."*
- **Honest:** a stricter "cloudy-sky" alert rule cut false alarms 59 → 35 but lost 13 real planted faults, so we kept it **off**.
- *Say:* "We don't have a cloud camera — we read the sky from the sunlight itself, and we measure exactly how much
  power clouds and heat cost each day. Operators only need to chase the red bar."

## 9. Scalability
- Works for **any plant, any number of inverters**: the model learns each plant from its own data.
- One command rebuilds everything (`python run_all.py`, ~97 s for 44 inverters × 34 days on a laptop).
- **Solar Site Planner:** type any place in India + plant size → free NASA POWER satellite weather → expected
  energy per month, using the heat effect we measured. 100 kW, flat panels: Delhi 1,271, Jaipur 1,413,
  Chennai 1,387 kWh per kW per year.
- **Accuracy (honest):** backtest on our plant 2.4% per day on unseen days; within 0.3–6.5% of the EU's PVGIS calculator for the 3 cities.
- Next step: live 15-minute data stream instead of replay.
- *Honest:* we have not benchmarked 1,000 inverters.

## 10. Competitive advantage
| | Basic SCADA threshold alarm | Notebook analysis | **SolarSense** |
|---|---|---|---|
| Knows what output *should* be for the weather | ✗ | sometimes | **✓** |
| Explains each alert in plain words | ✗ | ✗ | **✓** |
| Loss in kWh and ₹ per alert | ✗ | rarely | **✓** |
| Validated detection rate, incl. what it misses | ✗ | ✗ | **✓** |
| Separates weather losses from fixable fault losses | ✗ | rarely | **✓** |
| Operator workflow (acknowledge / resolve / export) | partly | ✗ | **✓** |

## 11. Future roadmap
- Live data feed + email/SMS alerts.
- More seasons of data (we only have May–June) → better accuracy all year.
- String-level data → pinpoint the exact panel string.
- Sourced tariff and cost data; tilted panels and real plant designs in the Solar Site Planner.
- Plant GPS location → a physical clear-sky model instead of our data-learned curve.
- *Close:* "SolarSense finds the losses in minutes, explains them, and puts a rupee value on them."
