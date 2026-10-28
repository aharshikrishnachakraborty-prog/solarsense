# 27 tough judge questions — honest answers

Numbers come from `key_numbers.md` (sources listed there). If you don't know an answer on stage, say
"we didn't measure that" — never guess.

**1. You only have 34 days of data. Is that enough?**
Enough to show the method works, not enough to claim year-round accuracy. All 34 days are May–June, so we
don't know how the model behaves in monsoon or winter. That's our first roadmap item: more seasons.

**2. Where are these plants? Does location matter?**
The dataset doesn't say — there is no GPS in it, so we never claim a location. It doesn't matter for our
method: the model learns each plant from its own sunlight sensor.

**3. Plant 1's numbers looked broken. What did you do?**
Its DC power was physically impossible: inverters seemed to keep only 9.8% of their input (Plant 2: 97.9%).
We computed a correction factor of **10.001** from the data, applied it, and labelled it an ASSUMPTION
everywhere. AC power — which we use for detection — was not changed.

**4. How does "expected output" work?**
A Random Forest learns, from the first 24 days, how much power each inverter makes for a given sunlight,
panel temperature, air temperature and time of day. Then for every 15 minutes it predicts what the inverter
*should* make. Actual far below expected = possible fault.

**5. Why a Random Forest and not something simpler?**
Honestly, the simple physics formula is almost as good: on healthy readings R² **0.9764** (physics) vs
**0.9758** (forest) for Plant 1. We kept both: the forest had slightly lower average error on the test days,
so it was chosen, and the physics formula proves the result isn't a black-box trick — sunlight explains
almost everything.

**6. What does R² 0.96 mean?**
The model explains 96% of the ups and downs in Plant 1's power on days it had never seen. A value of exactly
1.00 would be suspicious (it would mean the model saw the answers); ours is high but not perfect.

**7. Plant 2's R² is 0.12. Isn't your model bad there?**
On healthy readings it's **0.84**. The 0.12 is because Plant 2 has many real outages: 954 test readings with
strong sun and ~0 output. The model correctly says "should be producing" — those big misses *are* the faults
we detect. Plant 2's model is still weaker (15.5% average error vs 5.7%), and we say so.

**8. How did you test fault detection without labelled faults?**
We planted faults ourselves in healthy test days: 95 trips, 95 underperformance, 95 data gaps, 20 slow
soiling cases — and ran the exact same detector. Trips and gaps: 100% caught. Underperformance: 71.6%.
Soiling: 80%.

**9. Isn't that test too easy, since you made the faults?**
For trips and gaps, partly — planted faults are cleaner than real ones. That's why we also report what we
miss: when output only drops to 80–85%, we catch **5.6%**. And we list the caveats openly.

**10. How many false alarms do you get?**
At our default settings, none on the healthy test days — but that's optimistic, because "healthy days" were
chosen as days the detector was quiet. The true false-alarm rate needs labelled data. We did measure the
trade-off: the most sensitive setting catches 98.9% but raises **59** false alarms.

**11. How do you tell a cloud from a fault?**
A cloud dims all 22 inverters together, and the plant's sunlight sensor sees it. An alert also needs the
inverter to be clearly below its *neighbours* at the same moment (peer comparison). Every trip reason even
says what % of neighbours were down.

**12. Where does the ₹3/kWh tariff come from?**
It's an **assumption**, labelled everywhere. [Before presenting: cite a real tariff source, update
`TARIFF_INR_PER_KWH` in `engine/config.py`, re-run `python run_all.py` — every ₹ number updates.]

**13. How sure is the "₹2.99 crore per year" figure?**
It's a simple estimate: 34 days of loss scaled to 365 days, assuming nothing is fixed and every month looks
like May–June. We show it as an estimate, never as a fact.

**14. Why are there 429 alerts — won't operators ignore them?**
358 are inverter trips, mostly in Plant 2 — a typical one lasts hours and loses thousands of kWh, so they
really matter. The dashboard sorts by severity and loss, shows "Needs attention" first, and data-quality
notices are kept out of the alert count.

**15. Plant 2 trips mostly between 9 and 11 am. Why?**
We don't know — the data can't tell us the cause. It could be grid limits, inverter settings or a recurring
fault. What we *can* say: it repeats almost daily on many inverters, so it's worth a site investigation.

**16. Could this scale to 1,000 inverters or real-time data?**
The method doesn't depend on the number of inverters, and the full rebuild takes ~97 s for 44 inverters ×
34 days on a laptop (most of that is the validation test). We have **not** benchmarked 1,000 inverters. For
real time, the same pipeline would run every 15 minutes on the newest readings.

**17. What does it cost to run?**
Everything is free and open-source (Python, scikit-learn, FastAPI, Chart.js); the demo runs on a laptop and
on a free hosting tier. We haven't costed a production deployment.

**18. What did the AI tool build, and what did your team do?**
Be honest: we used an AI coding assistant (Claude Code) to write most of the code, phase by phase. The team
set the goals and rules, approved every plan, checked the results (e.g. caught that Plant 2's low R² comes from
outages), decided the thresholds and trade-offs, and can explain every part. [Each member: be ready to explain
your phase in your own words — see `explain_like_im_new.md`.]

**19. Did you find any slow degradation (dust)?**
No — and we didn't force it. The steepest real trend was −0.24% per day, within Plant 2's normal day-to-day
noise. Our planted-soiling test shows the rule works for faster declines (80% caught), but slow soiling below
0.5% per day over only 10 days was not caught.

**20. What are your biggest limitations?**
34 days in one season; one weather sensor per plant; no labelled faults; an assumed tariff; small dips under
20% usually missed by design; overheating can only be judged plant-wide. All are listed on the About page.

---

## Weather intelligence (Phases W1–W6)

**21. Your data has no cloud sensor — how do you know it's cloudy?**
We read it from the sunlight. For every 15-minute time of day we take a high percentile (95th) of the sunlight
over all 34 days — "what a clear sky gives at this time". Clear-sky index = actual ÷ that. Around 1 = clear,
below 0.3 = overcast, and fast flickering = passing clouds. Checks: on each plant's 3 sunniest days the midday
index is 0.94 (Plant 1) and 0.97 (Plant 2), and only 5–6% of readings flicker for one reading vs 18.5% if the
labels were random. It is an estimate, labelled ASSUMPTION everywhere.

**22. How accurate is your clear-sky reference with only 34 days and no GPS?**
Good enough to tell clear from cloudy, not a lab measurement. It works because at every time of day at least a
couple of the 34 days were clear. If some hour had been cloudy on almost every day, the curve would be too low
there and we would under-count clouds. With the plant's GPS location we would use a physical sun-position model
instead — that is on our roadmap.

**23. Is your temperature coefficient realistic?**
For Plant 1, yes: −0.39% per °C (95% range −0.45 to −0.33), inside the typical silicon range (−0.3 to −0.5), and
two other estimates agree (our physics model −0.41, a fit on alert-free readings −0.41). For Plant 2 the fit says
−0.30, but we say openly that it is weak evidence: sunlight and heat rise together, and inside narrow sunlight
bands the slope even flips. There is also only one panel-temperature sensor per plant.

**24. Couldn't a fault be hidden by a cloudy day?**
That is why we compare each inverter with its neighbours: a cloud dims all of them, a fault only one. We tested
it by planting faults on cloudy days: trips were caught 65 of 65 times; underperformance 45 of 65 (69%) — about
the same as on any day (68 of 95, 72%). We also tried a stricter rule for cloudy skies: it cut false alarms from
59 to 35 but lost 13 real planted faults, so we did NOT keep it. Instead every alert shows the sky and a
confidence level (High / Medium / Low).

**25. Why does weather matter to an operator if they can't control it?**
So they don't chase clouds. Our waterfall splits lost energy into natural (clouds + heat: 52,59,927 kWh over 34
days, both plants) and fixable (faults: 9,27,680 kWh). Only the red bar needs a technician. It also rules out
excuses: on 15 May, Plant 2's sky was clear (sunshine score 96), yet faults cost 38,049 kWh — so "it was cloudy"
is not the answer. And knowing heat costs ~6% of the clear-sky potential helps when planning ventilation or
cleaning schedules.

---

