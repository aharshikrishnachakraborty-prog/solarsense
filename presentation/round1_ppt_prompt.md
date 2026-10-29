You are building the Round 1 pitch deck for our hackathon team. Make a finished PowerPoint file (.pptx, 16:9).
Read this whole brief before starting. Every number below is real, computed by our working prototype —
use them exactly, never invent or round differently, never add statistics that are not in this brief.

============================================================
1. THE EVENT AND WHAT WE ARE JUDGED ON
============================================================
- Event: DEVIATHON 2.0. Round 1 = "PS Fit & Innovation Screening" (elimination round).
- Format: 5-minute presentation + 3-minute Q&A. Organisers ask for a 5–7 slide deck → make EXACTLY 7 slides.
- Round 1 marks (100): Problem understanding & PS alignment 25 · Innovation & originality 20 ·
  Solution approach & architecture 20 · Technical feasibility 15 · User needs & potential impact 10 ·
  Research & preparation quality 10.
- The organisers' Round 1 checklist — every item MUST appear somewhere in the deck:
  team name, team ID, members' names + contact details · PS number/title + concise problem interpretation ·
  target users, pain points, use cases, constraints · brief review of existing solutions + the gap ·
  proposed solution, key differentiator, expected outcome · system architecture / workflow diagram ·
  technology stack with brief justification · feasibility, key risks/assumptions + mitigation ·
  implementation plan and milestones.
- Rules: disclose significant third-party components and AI-assisted work; never fabricate results.

Mindset for the whole deck: WINNER MINDSET. There is no option other than winning. The tone is calm,
confident, proof-first: we did not just design this — we built it, tested it, and it is live. Bold claims,
each one backed by a number. No hype words without evidence, no apologising.

============================================================
2. OUR PROJECT (context you need)
============================================================
Product: SolarSense — an AI health monitor for solar power plants.
Problem statement: Meridian DEV-P01 (Application Development track).
PS text in short: solar operators learn about underperforming panels or inverters only after losses pile up.
Build an app that takes plant generation data, compares it with the expected output given the weather, and
flags likely faults with an estimated energy loss. Required deliverables: (1) dashboard of actual vs expected
output, (2) anomaly flags with a reason, (3) estimated loss in kWh and ₹, (4) alert list.
Target users: plant operators and O&M (operations & maintenance) engineers; plant owners (revenue).

Our one-line interpretation: "Every 15 minutes, compare what each inverter MADE with what it SHOULD have made
for that weather — and when it falls short, say what is wrong, why, and what it costs."

Data used: Kaggle "Solar Power Generation Data" (anikannal) — 2 real solar plants in India, 22 inverters each,
34 days (15 May – 17 Jun 2020), a reading every 15 minutes, 1,43,616 rows after cleaning.
Generation data per inverter (DC power, AC power, yield) + one weather sensor per plant (irradiation = sunlight,
module temperature, ambient temperature). No GPS location in the data — never claim a location.

How it works (the pipeline):
1. Clean & fix the data: we found Plant 1's DC power is 10.001× too large (AC÷DC was 0.0979 vs 0.9787 at Plant 2)
   and corrected it (labelled assumption); missing readings 4.22% (Plant 1) and 5.72% (Plant 2) — the worst
   Plant 2 inverters miss 28.3% of daylight readings; night rows are excluded.
2. Expected-output AI: scikit-learn Random Forest learns how much power each inverter should make from sunlight,
   panel temperature, air temperature and time of day. Honest time split: trained on the first 24 days, tested
   on the last 10 days it never saw. Plant 1 test R² = 0.96 (0.9603); average error 5.67% on healthy readings.
   A simple physics formula is kept as a cross-check (it scores about the same on Plant 1 — sunlight drives 98.7%
   of the model's decisions, which shows the model learned real physics, not noise).
   Plant 2 is noisier: R² 0.84 on healthy readings (15.46% error) — its sensor data is messier.
3. Peer comparison: each inverter is compared with its 21 neighbours under the same sky, so a cloud never looks
   like a fault.
4. Fault rules with reasons (6 types): inverter trip, underperformance, gradual degradation / soiling (dust),
   data gap / communication loss, overheating, sensor/data issue. Each alert has type, inverter, start/end,
   severity, the reason ("why"), evidence chart, energy + ₹ loss and a recommended action.
5. Loss engine: energy loss (kWh) = shortfall below expected during daylight; money = kWh × tariff.
   Tariff ₹3/kWh is an ASSUMPTION, configurable in one place (always say "at an assumed tariff").
6. Weather intelligence: splits every lost kWh into NATURAL (clouds, heat — nobody can fix) vs FIXABLE (faults).
   Measured panel heat penalty: −0.39 %/°C at Plant 1 — inside the −0.3 to −0.5 %/°C range on panel datasheets.
7. Results are saved to files → FastAPI serves them → web dashboard shows them (the website never runs ML itself,
   so the demo is instant and cannot crash mid-calculation).
8. Optional chat assistant (Google Gemini free tier): answers "summary of today / this week" in plain English.
   It only rephrases numbers our code already computed — the AI never decides what is a fault.
Principle to put on a slide: "The AI predicts. Rules decide. The LLM only explains."

The dashboard (working, live): Overview (KPI tiles, actual vs expected chart, alerts needing attention,
"Live replay" that plays a day in 15-minute steps like real-time monitoring, and a rotating 3D model of the plant
with one block per inverter coloured green/amber/red/grey by status — hover for its numbers, click to open it),
Plant page (health map of every inverter), Weather & Energy page (where did the energy go: natural vs fixable),
Inverters page (actual vs expected vs neighbours, power-vs-sunlight chart), Alerts page (every alert with its
"Why?" evidence, acknowledge / resolve). Login, works on phones, installable as an app.
Live link: https://ojasguptaa.github.io/solarsense/
Code: https://github.com/ojasguptaa/solarsense

Key results (all computed, all real):
- 429 alerts found: 358 inverter trips, 50 data gaps, 16 underperformance, 5 sensor issues; 203 critical.
- Energy lost to detected faults in 34 days: 9,27,680 kWh ≈ ₹27,83,041 (≈ ₹27.8 lakh) at an assumed ₹3/kWh.
- 99% of that energy was lost to inverter trips.
- Projected loss per year if nothing is fixed (ESTIMATE): 99,58,920 kWh ≈ ₹2.99 crore — for just these 2 plants.
- Plant 2 produced only 82% of what the weather allowed (Plant 1: 100%).
- Worst single inverter: Plant 2, LYwnQax7tkwH5Cb — 80,807 kWh lost, 24 alerts.
- Natural losses (clouds + heat) 52,59,927 kWh vs fixable losses (faults) 9,27,680 kWh — so operators stop
  chasing the weather and fix what can be fixed.
- Proof without fault labels: we PLANTED 305 synthetic faults into healthy data and ran the same detector:
  inverter trips 100% caught (95 of 95), 0 false alarms, alert in ~32 minutes; data gaps 100% caught, ~30 min;
  underperformance 71.6% caught; slow soiling 80% caught. Honest weak spot: very small dips (output still
  ≥ 80%) only 5.6% caught — on purpose, to avoid false alarms.
- Trips planted on cloudy days: 65 of 65 caught — clouds do not fool it.
- 110 automated tests pass. Runs free on a normal 8 GB laptop. ₹0 software cost (open-source).

Tech stack (with the one-line justification to show on the slide):
- Python 3.12, pandas, NumPy — "Excel, but in Python": cleans and joins 1.4 lakh rows of plant data.
- scikit-learn Random Forest + linear physics baseline — accurate on small data, explainable, no GPU needed.
- Rules + peer comparison (+ optional Isolation Forest hint) — every alert has a reason a human can check.
- FastAPI + uvicorn — fast, standard Python web API; serves the data and the website.
- HTML, CSS, JavaScript, Chart.js, Three.js — no heavy framework; works on any laptop or phone.
- pytest — 110 automated checks.
- GitHub Pages — free hosting for the live demo.
- Google Gemini (free tier, optional) — plain-English summaries only.
- Disclosure line (must be on the stack slide, small): "Open-source libraries · public Kaggle dataset ·
  AI coding assistant (Claude) used during development — disclosed."

Timeline (what we already did):
- 20 Oct: data loading & cleaning, expected-output AI, fault rules, losses, planted-fault validation, API,
  full dashboard, live on GitHub Pages.
- 26 Oct: weather intelligence (sky condition, heat penalty, natural vs fixable losses, weather-aware checks).
- 28–29 Oct: login, installable app, chat assistant, power-vs-sunlight chart, 3D plant view.
Next (milestones): Round 2 — prototype validation pack (test evidence, limitations, demo backup);
Round 3 — live data connector (inverter / data-logger feed instead of files), e-mail/SMS alerts,
more plants, retraining across seasons, a real tariff from a published source.

Team details (I will fill these in — leave clearly marked placeholders):
[TEAM NAME] · [TEAM ID] · [MEMBER 1 NAME — role — phone/email] · [MEMBER 2 …] · [MEMBER 3 …] · [MEMBER 4 …]

============================================================
3. DESIGN
============================================================
- 16:9. Dark, premium "control room" look: background deep navy #0B1220 (subtle radial glow), text #E5E9EF,
  muted text #94A3B8, ONE accent: solar amber #F59E0B; status colours green #4ADE80, amber #FBBF24,
  red #EF4444, grey #94A3B8. Font: Segoe UI (or Inter); titles bold, big numbers huge.
- Very little text: max ~35 words of body text per slide; big numbers, diagrams and icons do the talking.
  Use simple shapes and line icons drawn in PowerPoint — NO emoji, NO clip-art, NO real company logos.
- Every slide: small footer "SolarSense · DEV-P01 · Team [TEAM NAME]" + slide number.
- Diagrams must be native, editable PowerPoint shapes (not images).
- I will attach these screenshots from our real app — place them where noted, with a thin amber border and
  rounded corners: 8_plant_3d_view.png (or 9_plant_3d_view_dark.png), 2_alert_why_panel.png,
  5_validation_proof.png, 7_weather_energy_waterfall.png. If an image is missing, leave a labelled placeholder box.

============================================================
4. WOW FACTOR: MORPH TRANSITION FROM SLIDE 1 TO SLIDE 2
============================================================
Make the jump from slide 1 to slide 2 a cinematic PowerPoint MORPH:
- Slide 1 has: a large glowing amber sun (circle with soft glow) top-centre, a row of tilted solar panels
  (dark blue rounded rectangles with thin grid lines) across the bottom, the title "SolarSense" centred, and the
  big number "₹27.8 lakh" small and faded.
- Slide 2 has the SAME objects, transformed: the sun shrinks and flies to the top-left as the logo mark; the
  title shrinks into the slide header; one panel in the row turns RED (a failed inverter) while the others stay
  blue; "₹27.8 lakh" grows huge in the centre-right with its caption "lost to faults in just 34 days, 2 plants
  (at an assumed ₹3/kWh)".
- To make Morph match objects, give each shared shape the SAME name on both slides, starting with "!!"
  (e.g. "!!sun", "!!title", "!!panel1"…"!!panel6", "!!bignumber").
- Set slide 2's transition to Morph (option "Objects", duration 2.0 s). In python-pptx this needs raw XML in
  slide 2, placed right after <p:clrMapOvr> (before <p:timing> if present):
  <mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">
    <mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">
      <p:transition xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" spd="slow" p14:dur="2000">
        <p159:morph option="byObject"/></p:transition>
    </mc:Choice>
    <mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback>
  </mc:AlternateContent>
- All other slides: a subtle Fade or Morph transition (0.7 s) — keep it classy, no spinning or bouncing effects.
- If you cannot add the transition in the file, still build both slides with the "!!" names and tell me the
  manual steps (select slide 2 → Transitions → Morph → Effect Options → Objects). Note: Morph plays in
  PowerPoint 2019 / Microsoft 365, not in Google Slides.

============================================================
5. THE 7 SLIDES (content + timing; total 5:00)
============================================================
Slide 1 — Title / hook (0:25)
"SolarSense" · tagline: "Know what's wrong, why, and what it costs — before the losses pile up."
PS: Meridian DEV-P01 · Application Development track · DEVIATHON 2.0 · Team name + ID + members + contacts
(placeholders) · live link. Morph objects as described.

Slide 2 — The problem we are solving (PS fit) (0:50)
Header "Losses are found too late". Big number ₹27.8 lakh (morph). Our one-line interpretation.
Users: plant operators · O&M engineers · owners. Pain points: faults noticed only in end-of-month yield;
dashboards show power, not "what it should be"; clouds trigger false alarms; no ₹ figure to decide what to fix first.
Use cases: morning check "which inverter needs a technician today?"; alert with reason; weekly/monthly loss report.
Constraints: only generation + weather data, 15-minute readings, no GPS, dirty data (Plant 1 DC 10× wrong, up to
28.3% missing readings), must run free on a normal laptop.
A strip of 4 ticks: "PS deliverables covered: Actual vs expected dashboard ✓ · Fault flags with reason ✓ ·
Loss in kWh and ₹ ✓ · Alert list ✓" (use drawn tick icons, not emoji).

Slide 3 — What exists today, and the gap (0:40)
Three short cards of typical approaches + their weakness:
(1) Inverter / SCADA monitoring portals — show live power and the inverter's own error codes; do not know what
the output SHOULD be, so partial underperformance slips through; no ₹ impact.
(2) Fixed thresholds ("alert if power < X") — every cloud becomes a false alarm.
(3) Manual monthly yield reports — losses discovered weeks late.
(4, small) Black-box ML anomaly scores — flag "unusual" without a reason operators can trust.
The gap (one bold line): "No simple, free tool combines weather-aware expected output, neighbour comparison,
a human reason AND a rupee value for every alert."
Our differentiators (5 short badges): Weather-aware expected output · Peer comparison (clouds don't fool it) ·
Every alert explains "why" + action · Natural vs fixable loss split · Proven with 305 planted faults.
Small research line: "We studied the data deeply: found a 10× sensor error, 28% data gaps, and a −0.39 %/°C
heat penalty that matches panel datasheets."

Slide 4 — Solution and architecture (0:55)
A clean left-to-right flow diagram (native shapes, amber arrows):
Plant data (4 CSV files) → Clean & fix → Expected-output AI (Random Forest, checked by physics formula) →
Compare: actual vs expected + vs 21 neighbours → Fault rules (6 types, with reasons) → Loss engine (kWh + ₹) →
Saved results → FastAPI → Dashboard (Overview + 3D plant · Plant · Weather & Energy · Inverters · Alerts) +
optional chat assistant.
Under it, a highlighted principle bar: "The AI predicts. Rules decide. The LLM only explains."
Small screenshot: 8_plant_3d_view.png (bottom-right corner) captioned "Live: every inverter, coloured by health".

Slide 5 — Tech stack and feasibility: it already works (0:45)
Left: tech stack table (tool → why we chose it) from section 2, plus the disclosure line.
Right: "Proof it is feasible" big-number tiles:
R² 0.96 on 10 unseen days · 100% of planted trips caught, 0 false alarms, ~32 min · 305 planted faults tested ·
429 real alerts found · 110 automated tests passing · ₹0 software cost, runs on an 8 GB laptop.
Small screenshot: 5_validation_proof.png or 2_alert_why_panel.png. Live link + GitHub link.

Slide 6 — Risks, assumptions and our plan (0:45)
Risk → mitigation table (5–6 rows):
Dirty data (10× DC error, gaps) → automatic checks, documented fix; gaps become their own alert, counted as
"at risk", never as confirmed loss.
Clouds cause false alarms → expected output from measured sunlight + neighbour comparison; 65/65 trips caught on
cloudy days.
No official fault labels → 305 planted faults with honest scores, including our weak spot (small dips 5.6%).
Tariff unknown → ₹3/kWh clearly labelled ASSUMPTION, one setting to change.
Only 34 days of data → yearly figure labelled estimate; retrain across seasons next.
Demo failure → online copy on GitHub Pages + screenshots; dashboard works even if the chat AI is off.
Milestones timeline (horizontal): 20 Oct core engine + dashboard live → 26 Oct weather intelligence →
29 Oct 3D plant + chat → Round 2 validation pack → Round 3 live data connector + SMS/e-mail alerts + more plants.

Slide 7 — Impact and close (0:40)
Expected outcome: trips flagged in ~30 minutes instead of at month-end · operators fix the right inverter first,
ranked by ₹ · weather losses separated so nobody chases clouds.
Big numbers: "₹27.8 lakh lost in 34 days → ≈ ₹3 crore a year at stake for just 2 plants (estimate, assumed
tariff)" · "52.6 lakh kWh natural vs 9.3 lakh kWh fixable".
Optional image: 7_weather_energy_waterfall.png.
Closing line, large: "SolarSense — every lost kilowatt-hour, found, explained and priced."
Footer: live link + "Thank you — questions welcome."

============================================================
6. SPEAKER NOTES (very important)
============================================================
Write speaker notes for EVERY slide, in simple English an 18-year-old can say naturally (short sentences,
no jargon without a one-line explanation). Structure each slide's notes exactly like this:
- SAY (script, timed to the slide's seconds above; first person plural "we").
- KEY NUMBERS on this slide and what each one means in one simple sentence.
- IF THE JUDGES ASK… — 5 to 7 likely questions about THAT slide with short, honest answers (2–3 sentences)
  using only facts from this brief. Include at least these where they fit:
  • Why Random Forest and not deep learning? (small data — 34 days; fast; explainable; no GPU; and we checked it
    against a physics formula, which scores about the same on Plant 1 — that is honesty, not weakness.)
  • If physics does as well, why use AI? (Plant 2 is messy and temperature/time effects vary per inverter; the
    model adapts automatically; the physics formula stays as a safety check.)
  • How do you know alerts are correct without fault labels? (planted 305 known faults, measured what we caught,
    published the weak spot.)
  • Won't clouds cause false alarms? (expected output uses the measured sunlight; neighbours under the same cloud
    drop too; 65/65 trips caught on cloudy days.)
  • Plant 2 accuracy is lower — why? (its sensor data is noisier and many readings are missing; on healthy
    readings R² is 0.84; detection leans on neighbour comparison there.)
  • Where does ₹3/kWh come from? (an assumption, labelled everywhere, changeable in one setting; we will replace it
    with a published tariff.)
  • Is this live real-time data? (the dataset is historical; "Live replay" plays a real day in 15-minute steps
    exactly as live monitoring would; in a real plant the same API would read the inverter/data-logger feed.)
  • What hardware/sensors does a real plant need? (inverter power readings + one sunlight (irradiance) sensor +
    panel temperature sensor — most plants already have them.)
  • Does the chat AI make things up? (it only rephrases numbers our code computed; turn it off and everything
    still works.)
  • Did you use AI tools? (yes, an AI coding assistant helped write code; we designed the approach, chose the
    thresholds and trade-offs, tested everything and can explain every part — disclosed on the stack slide.)
  • Can it scale to more plants? (each plant is processed the same way; results are precomputed files, so adding
    plants means more files, not a slower website.)
  • What's your weak spot? (very small dips are caught only 5.6% — chosen on purpose to avoid false alarms.)
- ONE-LINE BACKUP if the speaker blanks.

Also add, after the 7 slides, 2 hidden backup slides (not counted in the 7, marked "BACKUP"):
B1 — Planted-fault validation table (all numbers above). B2 — Data quality findings (10× DC fix, missing readings,
night removal). Same design, with notes.

============================================================
7. FINAL CHECK BEFORE YOU GIVE ME THE FILE
============================================================
- Exactly 7 main slides + 2 hidden backup slides; total spoken time 5:00 or less.
- Every Round 1 checklist item from section 1 is visible somewhere — list where, slide by slide, in your reply.
- Every number matches this brief exactly; every ₹ figure says "assumed tariff" nearby.
- No emoji, no real company logos, no invented statistics, no claim of a plant location.
- Slide 1 → 2 morph works (shared "!!" names + Morph transition).
- Speaker notes present on every slide.
Then give me the .pptx file.
