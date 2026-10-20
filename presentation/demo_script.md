# Demo script — 2 minutes

**Before you start (5 minutes before your slot):**
1. Open the live site (Render) **2 minutes early** — the free server sleeps and needs ~1 minute to wake up.
   Backup: run locally (`uvicorn api.main:app --reload`, open http://localhost:8000).
2. On **Alerts**, make sure nothing is left "Acknowledged" from rehearsals (open the alert → **Re-open**).
3. Choose **Plant 2** in the top bar. The date jumps to **27 May 2020 (highest loss)** by itself.
4. Close other tabs; zoom the browser to 100–110 % so the back row can read it.

| Time | Click | Say |
|---|---|---|
| 0:00 | **Overview**, Plant 2, 27 May 2020 | "This is Plant 2 on its worst day. Our takeaway line says it straight away: **14 inverters need attention — about 51,270 kWh lost, ₹1,53,809 at an assumed tariff.**" |
| 0:15 | Point at the tiles | "The plant made only **68%** of what the weather allowed. The dashed line is what our AI expected; the blue line is what really happened." |
| 0:25 | Set speed **4×**, click **▶ Live replay** | "Let's replay the day as if it were live." — pop-ups appear from about 07:30: "**New alert: Inverter trip.** We'd know within about half an hour, not at the end of the month." |
| 0:45 | **Pause**, click a pop-up (or the top "Needs attention" item, **P2-TRIP-0126**) | "Every alert explains itself: output **0 kW for 7.75 hours** while sunlight was strong; about **952 kW** was expected; **7,382 kWh** lost. And the recommended action: send a technician." |
| 1:05 | Click **Acknowledge** | "The operator acknowledges it — this is a work list, not just a chart." |
| 1:10 | Click the inverter link in the panel | "Here's that inverter: the red area is the alert, output is zero while its neighbours keep producing." |
| 1:25 | **Plant** page | "This health map shows every inverter on every day. Red = problem. You can see Plant 2's trips are not bad luck — they repeat." |
| 1:40 | **Validation** page | "How do we know it works? We planted 305 faults ourselves: **trips and data gaps caught 100%**, underperformance 71.6% — and we show what we miss: small dips only 5.6%, on purpose, to avoid false alarms." |
| 1:55 | Back to Overview | "SolarSense: finds losses in minutes, explains them, puts a rupee value on them." |

After the demo: **Re-open** the acknowledged alert (Alerts → P2-TRIP-0126 → Re-open) so the next run starts clean.

## Backup plan

| Problem | Do this |
|---|---|
| Live site slow / asleep | Wait 60 s and refresh; meanwhile talk through slide 3. If still down → local server. |
| No internet at the venue | Local server works offline **except the charts** (Chart.js comes from the internet). Use the screenshots in `presentation/figures/` (in this order: 1 → 2 → 4 → 3 → 5). |
| Laptop problem | Second team member's laptop with the project cloned and `uvicorn` already running. |
| Pop-ups don't appear | Replay date must be 27 May 2020 on Plant 2; press **Stop**, then **▶ Live replay** again. |

**Roles during the demo:** P4 clicks, P3 speaks the numbers, P2 takes model questions, P1 takes data questions.
