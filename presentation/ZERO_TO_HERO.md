# SolarSense — Zero to Hero 🌞

### The one file you need to understand, explain and present every part of SolarSense

> **Who this is for:** you. You built SolarSense with an AI assistant but haven't had time to learn the
> ideas behind it. This file starts from **nothing** and goes slowly. Every new word is explained the
> first time it appears. Every formula comes with an example using **our real numbers**.
>
> **How it is written:** short sentences, everyday examples (water, buckets, cars, classrooms), and
> after each chapter a small **"Check yourself"** quiz with answers. If a chapter feels hard, read it
> twice. That's normal. Nobody gets this in one go.

---

## 📚 Table of contents

- [Chapter 0 — How to use this guide (and the 60-second summary)](#chapter-0--how-to-use-this-guide)
- [Chapter 1 — How solar power works, from zero](#chapter-1--how-solar-power-works-from-zero)
- [Chapter 2 — Power vs energy: kW vs kWh (the most important chapter)](#chapter-2--power-vs-energy-kw-vs-kwh)
- [Chapter 3 — Sunlight, clouds and heat](#chapter-3--sunlight-clouds-and-heat)
- [Chapter 4 — Money: tariff, ₹, lakh and crore](#chapter-4--money-tariff--lakh-and-crore)
- [Chapter 5 — The problem we solve (DEV-P01)](#chapter-5--the-problem-we-solve-dev-p01)
- [Chapter 6 — Our data](#chapter-6--our-data)
- [Chapter 7 — How SolarSense works, step by step](#chapter-7--how-solarsense-works-step-by-step)
- [Chapter 8 — The website, page by page](#chapter-8--the-website-page-by-page)
- [Chapter 9 — Every library and tool, explained](#chapter-9--every-library-and-tool-explained)
- [Chapter 10 — Case studies from our own data](#chapter-10--case-studies-from-our-own-data)
- [Chapter 11 — How our product helps (and its honest limits)](#chapter-11--how-our-product-helps)
- [Chapter 12 — About Meridian, the judges' company](#chapter-12--about-meridian-the-judges-company)
- [Chapter 13 — Presentation kit](#chapter-13--presentation-kit)
- [Chapter 14 — Glossary and formula cheat-sheet](#chapter-14--glossary-and-formula-cheat-sheet)
- [Chapter 15 — Final self-test](#chapter-15--final-self-test)

---

# Chapter 0 — How to use this guide

## A 3-day study plan

| Day | Read | Goal for the day |
|---|---|---|
| **Day 1** | Chapters 0 → 5 | You can explain how solar works, the difference between kW and kWh, and what problem we solve. |
| **Day 2** | Chapters 6 → 9 | You can explain how SolarSense works, inside and out, and what every page of the website shows. |
| **Day 3** | Chapters 10 → 15 | You can tell the case-study stories, give the pitch, answer judge questions and pass the self-test. |

Keep these files open next to this one. They are already in the `presentation/` folder:

| File | What it is | When to use it |
|---|---|---|
| `key_numbers.md` | Every number we say, with where it comes from | Before you say any number on stage |
| `judge_qa.md` | 27 tough judge questions with honest answers | Day 3 practice |
| `slide_outline.md` | What goes on each slide | When making slides |
| `demo_script.md` | A 2-minute click-by-click demo | Rehearsing the live demo |
| `explain_like_im_new.md` | One page per team role | Splitting topics between team members |

## ⭐ The 60-second summary (learn this first, word for word)

> "Solar plants lose money when an **inverter** breaks or gets weak. Today, operators often notice only
> at the end of the month, when the energy is already lost.
>
> **SolarSense** fixes that. Every 15 minutes it looks at how strong the sunlight is and how hot the
> panels are, and asks an AI model: *how much power **should** this inverter make right now?* Then it
> compares that with what the inverter **actually** made.
>
> If an inverter is far below what it should make, and also below its neighbours under the same sky,
> SolarSense raises an **alert**. The alert says **why** in plain words, how much energy was lost in
> **kWh**, what that is worth in **₹**, and **what to do**.
>
> It also reads the sky from the sunlight itself, so it can tell **natural losses** (clouds and heat,
> which nobody can fix) from **fixable losses** (faults). We proved it works by planting 305 fake faults:
> it caught **100% of inverter trips** within about half an hour."

If you remember only this paragraph, you can already survive a conversation with a judge. The rest of
this file explains every word in it.

---

# Chapter 1 — How solar power works, from zero

## 1.1 The sun sends energy

The sun constantly sends energy to Earth as **light**. You feel it as warmth on your skin.

Light is made of tiny packets of energy called **photons**. Think of photons as tiny invisible balls
flying from the sun at the speed of light.

## 1.2 A solar cell turns light into electricity

A **solar cell** is a thin slice of a special material, usually **silicon** (the same material used in
computer chips; it comes from sand).

**Like you're 5:** imagine a playground slide full of children (the **electrons**) sitting at the top,
not moving. A photon is like a friendly push. When a photon hits the cell, it pushes an electron, and
the electron starts moving. **Moving electrons = electricity.** The cell is built so the electrons can
only move one way, out through a wire. That one-way flow is a current.

- One small cell makes only a tiny amount of power.
- So we join about 60–72 cells into a **solar panel** (also called a **module**). Our data uses the
  word *module* in "module temperature", and it simply means the panel.
- Many panels are wired in a line, like beads on a necklace. That line is called a **string**.
- A big solar plant has thousands of panels in hundreds of strings.

```
  ☀️ sunlight
     │
     ▼
 [cell][cell][cell]...   → a PANEL (module)
 [panel]-[panel]-[panel] → a STRING
 many strings ───────────→ an INVERTER   (this is what SolarSense watches)
 many inverters ─────────→ the PLANT ──→ the electricity GRID ──→ homes and factories
```

## 1.3 DC and AC: why we need an inverter

Panels make **DC** electricity: **Direct Current**. It flows in **one direction only**, like a
battery.

- **Like you're 5:** DC is like a river that always flows the same way.

Homes and the electricity grid use **AC**: **Alternating Current**. It quickly changes direction back
and forth (50 times per second in India), like what comes out of a wall socket.

- **Like you're 5:** AC is like a saw going forward and back, forward and back.

The **inverter** is the box that turns DC into AC. It "inverts" the electricity.

```
Panels ──DC──▶ [ INVERTER ] ──AC──▶ Grid
 (battery-like)   (the translator)   (wall-socket-like)
```

A good inverter keeps about **95–99%** of the DC power and loses a little as heat. So **AC is always a
bit less than DC.** Remember this: it's how we caught the broken data in Plant 1 (Chapter 6).

## 1.4 Why SolarSense watches inverters

In our data, each plant has **22 inverters**. Each inverter collects power from many strings.

- If an **inverter stops**, every panel behind it is wasted, even though the sun is shining.
- We don't have data for single panels or strings. We **do** have data for each inverter every
  15 minutes.
- So the **inverter is our "unit of monitoring"**, like a teacher watching each student in a class.

The data calls each inverter a `SOURCE_KEY` (a code like `LYwnQax7tkwH5Cb`). It's just the inverter's name tag.

## 1.5 What can go wrong in a solar plant?

| Problem | What happens, in simple words | What it looks like in data |
|---|---|---|
| **Inverter trip** | The inverter switches itself off (fault, grid problem, overheating) | Sun is strong, but output ≈ 0 |
| **Underperformance** | Some strings broken, a loose wire, shade | Output clearly lower than it should be |
| **Soiling / degradation** | Dust on panels, panels ageing | Output slowly falls day after day |
| **Data gap** | The data logger or network fails | No readings at all |
| **Overheating** | Panels very hot, poor airflow | Hot panels and the whole plant low |
| **Sensor problem** | A meter is wrong | Impossible numbers (for example AC bigger than DC, or DC 10× too big) |

These are exactly the **6 fault types** SolarSense detects. More in Chapter 7.

## 1.6 Who runs a solar plant?

- **Plant operator:** watches the plant every day (like a shop manager).
- **O&M engineer** (Operations & Maintenance): the person who goes and fixes things (like a mechanic).
- **Owner / investor:** paid for the plant and earns money from every unit of electricity sold.

All three lose money when a fault goes unnoticed. SolarSense is built for the **operator** and the
**O&M engineer**.

### ✅ Check yourself (Chapter 1)
1. What does an inverter do? → *It converts DC from the panels into AC for the grid.*
2. Is AC normally bigger or smaller than DC? → *A little smaller, because the inverter loses a few % as heat.*
3. Why do we watch inverters and not single panels? → *The data only has readings per inverter, and an inverter failure wastes every panel behind it.*
4. What is a "module"? → *Another word for a solar panel.*

---

# Chapter 2 — Power vs energy: kW vs kWh

> 🔑 **This is the most important chapter.** Judges will notice right away if you mix up kW and kWh. Read it twice.

## 2.1 The car example

Think of a car:

| Car | Electricity | Unit |
|---|---|---|
| **Speed**: how fast you are going *right now* (km/h) | **Power**: how fast electricity is being made *right now* | **kW** (kilowatt) |
| **Distance**: how far you went in total (km) | **Energy**: how much electricity was made in total | **kWh** (kilowatt-hour) |

- The **speedometer** shows speed. The **odometer** shows distance.
- The inverter's live reading (`AC_POWER`) is like the speedometer: **power in kW**.
- What we sell, and what we lose, is like the distance: **energy in kWh**.

## 2.2 The water-tap example

- **Power (kW)** = how fast water flows out of a tap (litres per minute).
- **Energy (kWh)** = how much water ends up in the bucket (litres).

If the tap flows faster, or flows for longer, the bucket gets more water.

## 2.3 The one formula you must know

```
Energy (kWh) = Power (kW) × Time (hours)
```

Examples:
- A 1 kW heater running for 1 hour uses **1 kWh**.
- A 1 kW heater running for 3 hours uses 1 × 3 = **3 kWh**.
- A 2 kW machine running for half an hour uses 2 × 0.5 = **1 kWh**.

**In India, 1 kWh = 1 "unit"** on your electricity bill. When your parents say "we used 300 units
this month", they mean 300 kWh. That's a great example to use on stage.

## 2.4 Why SolarSense multiplies by 0.25

Our data has **one reading every 15 minutes**.

15 minutes = 15 ÷ 60 hours = **0.25 hours** (a quarter of an hour).

So the energy made in one 15-minute slot is:

```
Energy in one slot (kWh) = Power (kW) × 0.25
```

This is `INTERVAL_HOURS = 0.25` in `engine/config.py`. You'll see "× 0.25" all over our code. Now you know why.

**Worked example:** an inverter makes 1,000 kW for one 15-minute slot.
Energy = 1,000 × 0.25 = **250 kWh**.

There are 24 × 4 = **96** slots in a day (`READINGS_PER_DAY = 96`).

## 2.5 Big units

| Unit | Equals | Everyday feel |
|---|---|---|
| 1 **W** (watt) | — | an LED bulb uses a few watts |
| 1 **kW** (kilowatt) | 1,000 W | an iron or a small heater |
| 1 **MW** (megawatt) | 1,000 kW | a small solar plant |
| 1 **GW** (gigawatt) | 1,000 MW | a giant power station |
| 1 **kWh** | 1 kW for 1 hour | 1 "unit" on the bill |
| 1 **MWh** | 1,000 kWh | |

## 2.6 Capacity: the size of a solar plant

When people say "a **100 kW** solar plant", they mean its **maximum power** in perfect sunlight. That's
its **size**, like saying "a car with a top speed of 180 km/h". It doesn't tell you how much energy it
makes in a year, because the sun isn't always perfect.

That's why we also use **specific yield** (see Chapter 4): kWh made per year for every 1 kW of size.

### ✅ Check yourself (Chapter 2)
1. An inverter shows 800 kW. Is that power or energy? → *Power (it's "right now").*
2. It keeps making 800 kW for 2 hours. How much energy? → *800 × 2 = 1,600 kWh.*
3. Why do we multiply by 0.25? → *Each reading covers 15 minutes, which is 0.25 hours.*
4. What is 1 "unit" on an Indian electricity bill? → *1 kWh.*
5. One inverter makes 1,200 kW for one 15-minute slot. Energy? → *1,200 × 0.25 = 300 kWh.*

---

# Chapter 3 — Sunlight, clouds and heat

## 3.1 How strong is the sunlight? (Irradiation)

**Irradiation** (or *irradiance*) means **how strong the sunlight hitting the panels is**.

- It's measured in **kW per square metre (kW/m²)**: how much sun power falls on one square metre.
- At **night** it is **0**.
- At a **clear sunny noon** it is about **1.0 kW/m²**.
- On a cloudy noon it might be 0.3.

**Like you're 5:** irradiation is how hard the sun is "pushing" on the panels. A strong push makes more electricity.

**Rule number 1 of solar:** power goes up and down **almost exactly with sunlight**. Double the
sunlight and you get about double the power. Our AI model found that sunlight explains **98.7%** of
its decisions for Plant 1. That's why it can predict power so well.

In our data, sunlight is the `IRRADIATION` column from each plant's **one** weather sensor.

**Daylight:** we treat a 15-minute slot as "daylight" when irradiation is above **0.02**
(`DAYLIGHT_IRRADIATION_THRESHOLD`). Night rows are skipped, because you can't judge a solar inverter at night.

## 3.2 Clouds: reading the sky without a cloud camera

Our data has **no cloud sensor**. So how do we know if it was cloudy? We **read the sky from the
sunlight itself.** Here's the trick, step by step:

**Step 1, the clear-sky curve.** For each time of day (say 1:15 PM), look at the sunlight at 1:15 PM
on **all 34 days**. A clear day gives the most sunlight. We take a high value (the **95th
percentile**, which is roughly the 2nd-best day out of 34) and call it *"what a clear sky gives at 1:15
PM"*. Do this for every 15-minute slot and you get a smooth **bell-shaped curve**: low at sunrise,
highest at noon, low at sunset.

> **Why not take the very highest value?** One weird spike (sunlight bouncing off the edge of a cloud
> can briefly be *brighter* than a clear sky) could set the bar too high. The 95th percentile ignores
> such one-off spikes.

**Step 2, the clear-sky index (CSI).**

```
Clear-sky index (CSI) = actual sunlight ÷ clear-sky sunlight
```

| CSI | Sky label |
|---|---|
| 0.8 or more (and steady) | ☀️ **Clear** |
| 0.5 – 0.8 | ⛅ **Partly cloudy** |
| 0.3 – 0.5 | ☁️ **Cloudy** |
| below 0.3 | 🌫️ **Overcast** |

**Worked example:** at 1:15 PM a clear sky gives 0.9 kW/m². Today it's 0.45.
CSI = 0.45 ÷ 0.9 = **0.5**, so partly cloudy, right on the border with cloudy.

**Step 3, flicker (variability).** Passing clouds make the sunlight jump up and down from reading to
reading. If the CSI is high but jumping a lot (more than 0.1), we call it **Partly cloudy**, not Clear.

**Sunshine score (per day):** the day's total sunlight as a % of the clear-sky curve. About 95–100 means
a clear day; below 70 is a cloudy day.

**Did the trick work?** On each plant's 3 sunniest days, the midday CSI was **0.937** (Plant 1) and
**0.973** (Plant 2). It should be close to 1 on clear days, and it is. ✅

Our results over 34 days:
- Plant 1: 2 clear, 31 partly cloudy, 1 cloudy, 0 overcast days.
- Plant 2: 10 clear, 20 partly cloudy, 3 cloudy, 1 overcast day.

Code: `engine/weather.py`. It's labelled **ASSUMPTION** because it's learned from our 34 days, not from
a physics sun model. We can't use a physics model because the dataset doesn't include the plants'
**GPS location**. Never claim to know where the plants are.

## 3.3 Heat: hot panels make LESS power

This surprises most people: **solar panels work worse when they're hot.**

- Panels are tested and rated at **25 °C**. These are called "Standard Test Conditions" (STC).
- For every **1 °C hotter**, a typical silicon panel loses about **0.3% to 0.5%** of its power.
  This number is called the **temperature coefficient**, written like **−0.4 %/°C**. The minus sign
  means "less power".
- In India, panels in the midday sun easily reach **50–65 °C**.

**Like you're 5:** a panel is like a runner. On a cool morning it runs fast. On a very hot afternoon
it gets tired and slows down a bit.

**Two temperatures in our data:**
- `AMBIENT_TEMPERATURE` = the **air** temperature.
- `MODULE_TEMPERATURE` = the **panel's own** temperature. It's much hotter than the air in strong sun.

We measured that in full sun, Plant 1's panels get about **30 °C hotter than the air** (29.76 °C per 1
kW/m² of sunlight).

**We measured our own temperature coefficient** instead of copying a datasheet:
- **Plant 1: −0.392 %/°C** (95% range: −0.445 to −0.333). That's inside the typical silicon range
  (−0.3 to −0.5). ✅
- Plant 2: −0.304 %/°C. This is weaker evidence; we say so honestly (see `judge_qa.md` Q23).
- Hottest panel: 65.5 °C (Plant 1, 23 May) and 66.6 °C (Plant 2, 2 June).

### The heat-loss formula

```
Power lost to heat (%) = |coefficient| × (panel temperature − 25)
```

**Worked example:** a panel at **60 °C**, Plant 1 coefficient 0.392:
- Extra heat = 60 − 25 = 35 °C
- Loss = 0.392 × 35 = **13.7%**, so about 14% less power than the same panel at 25 °C.

**Worked example 2:** a panel at **50 °C**: 0.392 × 25 = **9.8%** less, so about 10%.
That's why `HOT_MODULE_TEMP_C = 50` counts as a "hot hour".

Over all 34 days, heat cost Plant 1 about **6%** of its clear-sky potential and Plant 2 about **5%**.

**How did we measure it?** (`engine/weather_temperature.py`)
1. Take only **healthy, sunny** readings (sunlight ≥ 0.3, the inverter in line with its neighbours).
2. Compute **efficiency = AC power ÷ sunlight** (power per unit of sun).
3. Draw a **straight line** of efficiency against panel temperature. The slope of the line tells us how
   much efficiency drops per °C.
4. **Bootstrap** for the 95% range: repeat the fit 500 times, each time on a random re-draw of the days,
   and see how much the answer wobbles. The middle 95% of those answers is the "95% range".
   **Like you're 5:** ask 500 slightly different groups of days the same question and see how much
   their answers agree.

### ✅ Check yourself (Chapter 3)
1. What is irradiation, and what is it at a sunny noon? → *Sunlight strength; about 1.0 kW/m².*
2. How do we know it was cloudy without a cloud sensor? → *We compare actual sunlight with a clear-sky curve learned from the brightest days (clear-sky index).*
3. CSI = 0.25. What's the sky? → *Overcast.*
4. Do hot panels make more or less power? → *Less, about 0.4% less per °C above 25 °C.*
5. A panel at 45 °C with coefficient −0.4 %/°C loses how much? → *0.4 × 20 = 8%.*

---

# Chapter 4 — Money: tariff, ₹, lakh and crore

## 4.1 Tariff

The **tariff** is the **price of 1 kWh** of electricity in rupees (₹/kWh). A solar plant sells its
energy to a buyer (often a state electricity company) at an agreed tariff.

**Our tariff: ₹3.0 per kWh. ⚠️ This is an ASSUMPTION.** It's a placeholder that the team hasn't
sourced yet. It's set in `engine/config.py` as `TARIFF_INR_PER_KWH = 3.0`.

> 🗣️ **On stage, always say "at an assumed tariff of ₹3 per kWh".**
> If you find a real source (for example a recent SECI solar auction result or a state tariff order),
> change the number in `engine/config.py`, run `python run_all.py`, and every ₹ number in the project
> updates by itself.

## 4.2 Energy lost → money lost

```
Money lost (₹) = Energy lost (kWh) × Tariff (₹/kWh)
```

**Worked example (real):** over 34 days, faults cost **9,27,680 kWh** across both plants.
Money = 9,27,680 × 3 = **₹27,83,041** (about ₹27.8 lakh).

## 4.3 Indian number format: lakh and crore

Our project writes big numbers the Indian way.

| Indian | International | Digits |
|---|---|---|
| 1 thousand = 1,000 | 1 thousand | 1,000 |
| **1 lakh = 1,00,000** | 100 thousand | 100,000 |
| 10 lakh = 10,00,000 | 1 million | 1,000,000 |
| **1 crore = 1,00,00,000** | 10 million | 10,000,000 |

So **₹2,98,76,759** = about **₹2.99 crore**, and **1,43,616 rows** = about 1.44 lakh rows.

> 🗣️ If a judge seems confused by commas, translate: "₹2.99 crore, about 3.6 lakh US dollars at
> roughly ₹83 a dollar." (The exchange rate is approximate. Check today's rate.)

## 4.4 Performance ratio (PR)

```
Performance ratio = actual energy ÷ expected energy
```

- **1.0 (100%)** = the plant made exactly what the weather allowed.
- **0.82 (82%)** = it made only 82% of what it should have.

Real results over 34 days:
- **Plant 1: 100%**, a healthy plant.
- **Plant 2: 82%** (0.8155): it lost about 18% of what the weather allowed, mostly to inverter trips.

> Careful: the *textbook* PR in the solar industry compares output with the panel's nameplate rating.
> **Our** PR compares output with **our model's expected output for that weather**, which is fairer for
> spotting faults. If asked, say: "our PR is actual ÷ AI-expected."

## 4.5 Specific yield (for planning new plants)

```
Specific yield = kWh per year ÷ plant size in kW     (unit: kWh per kW per year)
```

- Delhi **1,271**, Jaipur **1,413**, Chennai **1,387** kWh per kW per year.

So in Jaipur, every 1 kW of panels makes about 1,413 units of electricity a year.

## 4.6 The yearly projection, and why it's only an estimate

```
Projected yearly loss = loss in our 34 days × (365 ÷ 34)
```

9,27,680 kWh × 365 ÷ 34 ≈ **99,58,920 kWh per year ≈ ₹2.99 crore** (at the assumed tariff).

⚠️ This assumes the **whole year behaves like May–June** and **nothing is ever fixed**. Real life will
differ. Always call it an **estimate**.

## 4.7 What does solar cost to build? (general knowledge, cite before using)

These are **not from our project**. They are rough general facts. Only say them if you find a fresh source:
- Solar panels have become dramatically cheaper over the last 10–15 years.
- In India, large solar plants sell electricity at some of the **lowest tariffs of any power source**
  (auction results are often in the ₹2–3 per kWh range). That's one reason our ₹3 assumption is
  reasonable, but **it still needs a citation**.
- India has big national solar targets (for example the 500 GW non-fossil capacity goal for 2030) and
  rooftop schemes such as **PM Surya Ghar**. Check the latest MNRE figures before quoting them.

**The key business point (no citation needed, it's logic):** once a plant is built, the sunlight is
free. **Every hour an inverter is down is pure lost income.** Catching a fault in 30 minutes instead of
30 days saves real money.

### ✅ Check yourself (Chapter 4)
1. 500 kWh lost at ₹3/kWh = ? → *₹1,500.*
2. Is ₹3/kWh a measured fact? → *No, it's a labelled assumption, configurable in `engine/config.py`.*
3. Write 1 crore in digits. → *1,00,00,000 (10 million).*
4. Plant 2's PR is 82%. What does that mean? → *It made only 82% of the energy the weather allowed.*
5. Why is "₹2.99 crore per year" only an estimate? → *It scales 34 May–June days to a whole year and assumes nothing is fixed.*

---

# Chapter 5 — The problem we solve (DEV-P01)

## 5.1 The problem statement, in simple words

The Meridian hackathon, **Application Development track**, problem **DEV-P01**:

> Solar operators learn about underperforming panels or inverters **only after losses pile up**.
> Build an app that takes plant generation data, compares it with the **expected output given the
> weather**, and **flags likely faults with an estimated energy loss**.

**Like you're 5:** imagine a lemonade stand with 22 helpers. One helper falls asleep at noon. You only
find out at the end of the month when you count the money. SolarSense is the friend who taps you on
the shoulder **30 minutes** after the helper falls asleep and says: *"Helper #7 is asleep. You're losing
₹500 an hour. Go wake them up."*

## 5.2 What the judges asked for (4 deliverables), and where we deliver each

| # | Required | Where it is in SolarSense |
|---|---|---|
| 1 | **Dashboard of actual vs expected output** | Overview, Plant, Inverters pages (blue line = actual, dashed line = expected) |
| 2 | **Anomaly flags with a reason** | Every alert has a plain-English reason and a "Why?" panel with an evidence chart |
| 3 | **Estimated loss** (kWh and ₹) | On every alert, every day, every plant, plus the energy waterfall |
| 4 | **Alert list** | Alerts page: filter, search, sort, Acknowledge / Resolve, CSV export |

**Extras we built beyond the brief:** weather intelligence (natural vs fixable losses), a validation

## 5.3 Why it's hard (and why this is clever)

You can't just say "power is low → fault", because **power is supposed to be low** when it's cloudy, in
the morning, or in the evening. The question is always: **low compared with what?**

SolarSense answers: **low compared with what the weather allowed** (the AI's *expected* output) **and
compared with the neighbours under the same sky** (peer comparison). That's the whole idea.

---

# Chapter 6 — Our data

## 6.1 Where it comes from

- **Kaggle "Solar Power Generation Data" by anikannal**, free to download (Kaggle is a website full of public datasets).
- **Two solar plants in India.** The dataset does **not** say where they are (no GPS).
- **34 days:** 15 May to 17 June 2020 (one season: Indian summer).
- **One reading every 15 minutes.**
- **22 inverters per plant** and **1 weather sensor per plant**.
- The dataset doesn't state units. We read power as kW and energy as kWh, which is how this dataset is normally used.

## 6.2 The 4 files and their columns

| File | Rows | What it contains |
|---|---|---|
| `Plant_1_Generation_Data.csv` | 68,778 | Plant 1, every inverter, every 15 minutes |
| `Plant_1_Weather_Sensor_Data.csv` | 3,182 | Plant 1 weather sensor |
| `Plant_2_Generation_Data.csv` | 67,698 | Plant 2 inverters |
| `Plant_2_Weather_Sensor_Data.csv` | 3,259 | Plant 2 weather sensor |

**Generation columns** (one row = one inverter at one moment):

| Column | Meaning |
|---|---|
| `DATE_TIME` | When the reading was taken |
| `PLANT_ID` | Which plant (4135001 = Plant 1, 4136001 = Plant 2) |
| `SOURCE_KEY` | Inverter ID (its name tag) |
| `DC_POWER` | Power coming **in** from the panels (kW) |
| `AC_POWER` | Power going **out** to the grid (kW). **This is what we use.** |
| `DAILY_YIELD` | Energy made so far today (kWh). Turned out to be unreliable, so we don't use it |
| `TOTAL_YIELD` | Energy made over the inverter's whole life (kWh). Broken in Plant 2, not used |

**Weather columns** (one row = the plant's weather sensor at one moment):

| Column | Meaning |
|---|---|
| `AMBIENT_TEMPERATURE` | Air temperature (°C) |
| `MODULE_TEMPERATURE` | Panel temperature (°C) |
| `IRRADIATION` | Sunlight strength (≈ kW/m²) |

We join the two kinds of files on **time + plant**, so every inverter reading knows the sunlight and
temperature at that moment. After cleaning, the full table has **1,43,616 rows** (2 plants × 22 inverters × 34 days × 96 slots).

## 6.3 The problems we found (data detective work 🕵️)

Judges love this part. It shows you **checked** the data instead of trusting it blindly.

**Problem 1: Plant 1's DC power was impossible.**
- Remember: AC should be a bit *less* than DC (about 95–99%).
- Plant 2: AC ÷ DC = **0.9787** (97.9%). Normal ✅
- Plant 1: AC ÷ DC = **0.0979** (9.8%). That would mean the inverter throws away 90% of the power. Impossible ❌
- So Plant 1's DC numbers are about **10× too big** (a logging/units error).
- **Fix:** divide Plant 1's DC by a factor we **computed** from the data: 0.9787 ÷ 0.0979 ≈ **10.001**.
  It's labelled ASSUMPTION.
- **Important:** fault detection uses **AC** power, which we did **not** change.

**Problem 2: missing readings.**
- Plant 1 is missing **4.22%** of readings and Plant 2 **5.72%**.
- Four Plant 2 inverters miss **28.3%** of their daylight readings.
- **We never fill gaps with made-up numbers.** A silent inverter might be a broken one, so a gap is
  information. Gaps become **"Data gap / communication loss"** alerts.

**Problem 3: broken energy counters.**
- `DAILY_YIELD` sometimes goes *backwards* during the day (impossible for "energy so far today").
- `TOTAL_YIELD` in Plant 2 is sometimes 0 and goes backwards 1,161 times.
- **Fix:** we don't use them. We calculate energy ourselves: **AC power × 0.25 h.**

**Problem 4: different date formats.** Plant 1's generation file writes `15-05-2020 00:00` (day first)
and the others write `2020-05-15 00:00:00`. If you let the computer guess, it can swap day and month. We
state each file's exact format in `engine/config.py` (`DATE_FORMATS`).

Full details: `reports/data_quality.md`. Code: `engine/load_data.py`, `engine/clean_data.py`, `engine/explore_data.py`.

> 🗣️ **Say on stage:** "We checked every column and found 3 big problems: Plant 1's DC was 10 times
> too big, some readings were missing, and the energy counters were broken. We documented how we handled
> each one, and we never invented data."

### ✅ Check yourself (Chapter 6)
1. How many plants, inverters, days, and how often are readings taken? → *2 plants, 22 inverters each, 34 days, every 15 minutes.*
2. How did we know Plant 1's DC was wrong? → *AC ÷ DC was 9.8%, which is impossible; Plant 2 was a normal 97.9%.*
3. Do we fill missing readings? → *No. Gaps are kept and become data-gap alerts.*
4. Why don't we use DAILY_YIELD? → *It goes backwards sometimes, so we compute energy as AC × 0.25 h ourselves.*
5. Do we know where the plants are? → *No, the dataset has no GPS. Never claim a location.*

---

# Chapter 7 — How SolarSense works, step by step

## 7.0 The big picture

SolarSense has **two halves**:

1. **The engine (Python):** the "kitchen". It cooks all the results in advance and saves them to files.
2. **The website + API:** the "restaurant". The website (customer) asks the API (waiter) for results,
   and the API brings the pre-cooked answer from the kitchen's files.

```
 4 Kaggle CSV files
        │
        ▼
 ① LOAD & CLEAN ──────────── fix Plant 1 DC, keep gaps visible, join weather to inverters
        │
        ▼
 ② EXPECTED OUTPUT (AI) ──── "how much SHOULD each inverter make now?" (Random Forest + physics formula)
        │
        ▼
 ③ RESIDUAL & PEERS ──────── actual − expected, and "how am I doing vs my 21 neighbours?"
        │
        ▼
 ④ WEATHER ──────────────── read the sky from sunlight, measure the heat effect
        │
        ▼
 ⑤ FAULT RULES ──────────── 6 fault types → alerts with reason, severity, confidence, action
        │
        ▼
 ⑥ LOSSES ───────────────── kWh lost and ₹ lost (per alert, day, inverter, plant)
        │
        ▼
 ⑦ WATERFALL ────────────── where did the energy go? clouds / heat / faults / unknown
        │
        ▼
 ⑧ VALIDATION ───────────── plant fake faults, check we catch them (our proof)
        │
        ▼
 files in data/processed/ + reports/metrics.json
        │
        ▼
 ⑨ API (FastAPI) ─────────── serves results as JSON  ──▶  ⑩ WEBSITE (HTML + Chart.js)
```

**One command runs the whole kitchen:** `python run_all.py` (about 3 minutes; about 15 s with `--skip-validation`).

**All settings and thresholds** live in one file: `engine/config.py`. Change a number there, re-run,
and everything updates.

**Golden rule of the project:** *every number shown anywhere is computed by our code* and saved in
`reports/metrics.json`. Nothing is typed in by hand. Anything we had to guess is labelled **ASSUMPTION**
and listed in `reports/assumptions.md`.

---

## 7.1 Step ① — Load and clean (`engine/load_data.py`, `engine/clean_data.py`)

What happens:
1. Read the 4 CSVs, each with its exact date format.
2. Rename columns to friendly names (`AC_POWER` → `ac_kw`, `SOURCE_KEY` → `inverter`, …).
3. Build a **full grid**: every inverter × every 15-minute slot. If a reading is missing, the row still
   exists with `is_missing = True`. That's how gaps stay visible.
4. Fix Plant 1 DC (÷ 10.001).
5. Join the weather (sunlight, temperatures) to every inverter row.
6. Mark daylight rows (sunlight > 0.02).
7. Save as `data/processed/clean.parquet`.

**Parquet** is a fast, compact file format for tables, like a super-efficient Excel file. (Chapter 9.)

---

## 7.2 Step ② — Expected output: the AI part (`engine/expected_model.py`)

### The question
> "With **this** sunlight and **this** temperature, how much power **should** this inverter be making right now?"

The answer is called **expected power** (`expected_kw`).

### Why we need it
If an inverter makes 400 kW, is that good or bad? **It depends.** At a sunny noon it should make about
1,300 kW, so 400 is terrible. At 7 AM it should make about 300 kW, so 400 is great. Expected power gives
us the right **yardstick** for every moment.

### We built TWO models and compared them

#### Model A: the physics formula (the "simple baseline")

From physics we know two things: power is proportional to sunlight, and it drops a little as panels get
hotter than 25 °C. So:

```
expected AC power  ≈  k × irradiation × (1 − γ × (module_temp − 25))
```

- **k** = how many kW the inverter makes per unit of sunlight at 25 °C (its "size").
- **γ** (gamma) = how much power is lost per °C above 25 (the temperature coefficient as a fraction).

The computer **learns** k and γ from the data using **linear regression** (drawing the best-fitting
straight line through the points). Our learned values for Plant 1: **k = 1,453.28 kW, γ = 0.0041 per °C**
(that's 0.41% per °C, which matches our separate heat measurement of 0.39%. ✅ Nice cross-check.)

**Worked example (Plant 1, one inverter):** sunlight 0.8, panel at 45 °C.
- Temperature part: 1 − 0.0041 × (45 − 25) = 1 − 0.082 = 0.918
- Expected = 1,453.28 × 0.8 × 0.918 ≈ **1,067 kW**
- If the inverter actually shows 1,050 kW → healthy. If it shows 0 kW → something is wrong.

#### Model B: Random Forest (the "AI" model)

**Like you're 5: a decision tree** is a flowchart of yes/no questions:

```
Is sunlight > 0.6?
 ├─ yes → Is panel temp > 50 °C?
 │         ├─ yes → guess 1,050 kW
 │         └─ no  → guess 1,180 kW
 └─ no  → Is sunlight > 0.3?
           ├─ yes → guess 600 kW
           └─ no  → guess 150 kW
```

One tree can be a bit silly. So a **Random Forest** grows **100 different trees**. Each sees a slightly
different random sample of the data. Every tree makes a guess and we take the **average**.

**Like you're 5:** ask 100 friends to guess how many sweets are in a jar, then average their guesses.
The average is usually much better than any single friend.

The forest looks at 5 things (**features**):
1. `irradiation`: sunlight
2. `module_temp`: panel temperature
3. `ambient_temp`: air temperature
4. `hour_decimal`: time of day (for example 13.25 = 1:15 PM)
5. `inverter_code`: which inverter (each has its own small quirks)

Settings: 100 trees, max depth 14, at least 5 samples per leaf, random seed 42 (so every run gives the
same answer). Library: **scikit-learn** (`RandomForestRegressor`).

**Feature importance** (how much each feature mattered):

| Feature | Plant 1 | Plant 2 |
|---|---|---|
| Sunlight | **98.7%** | **94.7%** |
| Panel temp | 0.3% | 1.6% |
| Air temp | 0.2% | 1.3% |
| Time of day | 0.3% | 1.2% |
| Inverter | 0.5% | 1.2% |

→ **Sunlight explains almost everything.** That's good: it means the model is learning real physics, not tricks.

### Fair testing: the time split

- **Train** on the **first 24 days** (15 May – 7 June).
- **Test** on the **last 10 days** (8 – 17 June), which the model has **never seen**.
- **Never a random split.** In real life you predict the future from the past. A random split would let
  the model "peek" at days around the test days, which is cheating.

**Like you're 5:** you study chapters 1–7 and the exam is on chapters 8–10. If the exam had the same
questions as your homework, a high score wouldn't prove anything.

**One more trick:** when training, we **remove obvious outages** (sunlight ≥ 0.3 but output ≤ 1 kW), so
the model learns what a **healthy** inverter does. (Plant 1: 35 rows removed. Plant 2: 2,769 rows.)
Those rows stay in the test, because finding them is the whole point.

### The report card: R², MAE, MAPE

| Score | Simple meaning | Good value |
|---|---|---|
| **R²** ("R-squared") | How much of the ups and downs the model explains. 1.0 = perfect, 0 = useless | Close to 1 |
| **MAE** (Mean Absolute Error) | On average, how many kW the guess is off by | Small |
| **MAPE** (Mean Absolute % Error) | On average, how many **%** the guess is off by (only where actual ≥ 100 kW, because a % error on tiny numbers at dawn is misleading) | Small |

**Our results on the 10 unseen test days:**

| | Plant 1 | Plant 2 |
|---|---|---|
| Chosen model | Random Forest | Random Forest |
| R², all test rows | **0.9603** | 0.1208 (!) |
| R², healthy rows (outages excluded) | **0.9758** | **0.8387** |
| Physics formula R², healthy rows | 0.9764 | 0.8314 |
| MAPE | **5.67%** | 15.46% |
| MAE, healthy rows | 32.5 kW | 58.1 kW |

**How to explain these numbers:**

- **Plant 1 R² = 0.96:** "the model explains 96% of the ups and downs in power on days it never saw."
- **Why is Plant 2 only 0.12?** Because Plant 2 has **lots of real outages** (954 test readings with
  strong sun and ~0 output). The model correctly says *"you should be making 1,000 kW"* and the inverter
  makes 0. That counts as a big "error", **but that error IS the fault we want to find.** On healthy
  rows, Plant 2 scores **0.84**. Plant 2 is still harder to predict (15.5% error vs 5.7%), and we say so.
- **Why keep a Random Forest if physics is just as good?** Honest answer: they're almost equal (0.9764
  vs 0.9758). The forest had a slightly lower average error on all test days, so it was chosen. **The
  physics formula proves our AI isn't a black-box trick**: sunlight really does explain almost
  everything. Having both makes the result more believable.
- A perfect R² of 1.00 would be **suspicious** (it would suggest the model saw the answers).

Full report: `reports/model_card.md`.

---

## 7.3 Step ③ — Residual and peer comparison

### Residual: how far off is the inverter?

```
residual (kW)  = actual − expected
residual (%)   = 100 × (actual − expected) ÷ expected
```

- Residual ≈ 0% → behaving as expected. ✅
- Residual = −30% → making 30% less than it should. ⚠️
- Residual = −100% → making nothing. 🚨

(We only compute the % when expected ≥ 50 kW, to avoid dividing by tiny numbers at dawn and dusk.)

### Peer comparison: the classroom trick 🏫

**Like you're 5:** a class takes a test. One student scores 40%.
- If the **whole class** scored about 40%, the **test** was hard (= a cloud).
- If everyone else scored about 90%, **that student** has a problem (= a fault).

SolarSense does the same, every 15 minutes:
1. For each inverter: `actual ÷ expected` (its own "score").
2. Find the **median** score of all 22 inverters at that moment. (The **median** is the middle value
   when you line them up. It isn't fooled by one or two extreme values.)
3. **Peer ratio** = my score ÷ the class median.
   - Peer ratio ≈ 1 → I'm like my neighbours. ✅
   - Peer ratio = 0.5 → I'm doing half as well as my neighbours. 🚨

**Why this matters:** we only have **one** sunlight sensor per plant. If a cloud covers part of the
plant, the sensor might not see it. But all the inverters under that cloud dip **together**, so the
peer median dips too. Peer comparison stops clouds from causing false alarms.

Code: `add_residuals()` and `add_peer_comparison()` in `engine/expected_model.py`.

---

## 7.4 Step ④ — Weather (`engine/weather.py`, `engine/weather_temperature.py`)

Already explained in Chapter 3:
- **Sky** for every 15 minutes: clear-sky index → Clear / Partly cloudy / Cloudy / Overcast.
- **Heat**: measured temperature coefficient → how much power heat cost every 15 minutes.

```
power a 25 °C panel would make = expected ÷ (1 − share lost to heat)
heat loss                      = that − expected
```

---

## 7.5 Step ⑤ — Fault rules (`engine/detect_faults.py`)

### Why rules and not "let the AI decide"?
An operator needs to know **why** an alert happened and **what to do**. A rule like *"strong sun but 0
output for 30+ minutes"* is crystal clear. The AI's job is to provide the **expected value** that the
rules compare against. **The AI never decides alone.** This is a design choice; say it proudly.

### The 6 fault types (all thresholds in `engine/config.py`)

#### 1. 🔴 Inverter trip / outage
- **Rule:** sunlight ≥ **0.25** AND output ≤ **1 kW**, for at least **2 readings (30 minutes)**.
- **Means:** the inverter switched off while the sun was shining.
- **Action:** *Send a technician to check the inverter and grid connection; restart if safe.*
- The reason also says what % of the **other** inverters were down at the same time. If 50%+ were down,
  it's probably a plant-level or grid problem, not this inverter alone.

#### 2. 🟠 Underperformance
- **Rule:** actual at least **20% below expected** (residual ≤ −20%) AND at least **20% below the
  neighbours** (peer ratio ≤ 0.8), for at least **4 readings (1 hour)**.
- Both conditions are needed. "Below expected" alone could be a cloud the sensor missed; "below
  neighbours" proves it's this inverter.
- A tripped reading isn't also counted as underperformance (a trip already explains it).
- **Action:** *Inspect the strings for failed strings, loose connectors or shading.*

#### 3. 🟡 Gradual degradation / soiling (dust)
- **Rule:** every day, compute the inverter's performance relative to the plant median. Fit a straight
  line over the days. If it falls by at least **0.3% per day** AND at least **5% in total**, over at
  least **10 days** → alert.
- **Means:** slow, steady decline. Dust building up, or panels ageing.
- **Action:** *Schedule panel cleaning; if output doesn't recover, check for ageing.*
- **Honest result:** we found **no** real degradation in our 34 days (the steepest real trend was −0.24%
  per day, which is within normal noise). We didn't force one.

#### 4. 🔵 Data gap / communication loss
- **Rule:** no readings from the inverter during daylight for at least **30 minutes**.
- Energy during a gap is called **"at risk"**, not "lost". We can't see what happened, so we don't claim it.
- **Action:** *Check the data logger and network link.*

#### 5. 🔥 Overheating (plant level)
- **Rule:** panels at least **28 °C hotter than the air** AND the whole plant below **90%** of
  expected, for 30+ minutes.
- Plant-level only, because there's only **one** panel-temperature sensor per plant.
- **Action:** *Thermal check: ventilation, hotspots, inverter cooling.*

#### 6. ⚙️ Sensor / data issue
- **Rule:** impossible values found during cleaning (Plant 1 DC 10× too big, broken energy counters, AC > DC).
- **Action:** *Recalibrate or replace the sensor/meter.*

### Turning flagged readings into events
Flagged 15-minute readings in a row are **grouped into one event**. If one healthy reading sits
between two flagged ones, it's still one event (`MERGE_GAP_INTERVALS = 1`). This stops one noisy
reading from splitting an alert in two.

### Every alert gets…
| Field | Example |
|---|---|
| **ID** | `P2-TRIP-0126` (plant 2, trip, number 126) |
| **Inverter, start, end, duration** | 7.75 hours |
| **Reason** (plain English, real numbers) | "Output was 0.0 kW on average for 7.75 hours while sunlight was strong…; about 952 kW was expected." |
| **Energy lost (kWh) and ₹** | 7,382 kWh |
| **Severity** | Critical / High / Medium / Low |
| **Confidence** | High / Medium / Low |
| **Sky + weather sentence** | "Sky was clear (clear-sky index 0.98), so low output is NOT caused by clouds." |
| **Recommended action** | "Send a technician…" |
| **Status** | Open → Acknowledged → Resolved |

### Severity: how bad is it?
Decided by **energy lost**:

| Energy lost | Severity |
|---|---|
| ≥ 2,000 kWh | 🔴 Critical |
| ≥ 500 kWh | 🟠 High |
| ≥ 100 kWh | 🟡 Medium |
| less | ⚪ Low |

- An event lasting **4+ hours** goes up one level (long problems matter more).
- Data gaps are rated by **hours silent** and never above High (we can't prove energy was lost).

(Rough feel: one inverter makes about 1,000 kWh in a sunny hour, so 2,000 kWh ≈ two sunny hours of one inverter.)

### Confidence: how sure are we?
- Data gaps and sensor issues → **High** (missing or impossible readings are facts).
- Trips → **High**, or Medium under a difficult (overcast/flickering) sky.
- Underperformance → High on a clear sky, Medium otherwise, **Low** under a difficult sky. It goes up one
  level if the inverter is 50%+ below its neighbours.
- Degradation and overheating → Medium.

### Results on the real data
- **429 alerts** in total: **358 trips**, 50 data gaps, 16 underperformance, 5 sensor issues.
- **203 Critical.**
- Inverters with at least one alert: Plant 1 **11 of 22**, Plant 2 **22 of 22**.
- **99% of all lost energy is from inverter trips**, mostly in Plant 2, often between 9 and 11 AM. We
  **don't know why** (the data can't tell us); it could be grid limits or inverter settings. That's
  worth a site visit.

### Bonus: Isolation Forest "unusual day" hint (`engine/anomaly_score.py`)
- **Isolation Forest** is an AI method that "finds the odd ones out". **Like you're 5:** in a game of
  20 questions, a weird animal is guessed in very few questions because it's so different. Isolation
  Forest finds the data points that are easiest to separate from everyone else.
- We use it per inverter-day: it flagged **76** unusual days out of 1,496. **65.8%** of those also had a rule alert.
- It's **only a hint on the dashboard, never an alert**, because it can't say **why** something is
  unusual. We told it to expect about 5% unusual days (an ASSUMPTION it needs).

---

## 7.6 Step ⑥ — Losses (`engine/losses.py`)

### The loss formula, for every 15 minutes inside an alert

```
lost energy (kWh) = max(expected − actual, 0) × 0.25
```

- `max(…, 0)` means: if the inverter made *more* than expected, count 0, not a negative loss.
- Add up all the 15-minute slots of the alert → the alert's **energy loss**.
- × tariff → **₹ loss**.

**Worked example (real alert P2-TRIP-0126):** about **952 kW** expected, **0 kW** actual, for
**7.75 hours** (31 slots).
- Per slot ≈ 952 × 0.25 = 238 kWh.
- Total ≈ 952 × 7.75 ≈ **7,380 kWh** (the exact sum over each slot's own expected value is **7,382 kWh**).
- Money ≈ 7,382 × ₹3 ≈ **₹22,146** at the assumed tariff.

### Two kinds of energy, never mixed
| Kind | Meaning | Total (34 days, both plants) |
|---|---|---|
| **Confirmed loss** | We saw the inverter under-produce | **9,27,680 kWh** (≈ ₹27.8 lakh at ₹3) |
| **At risk** | Data gap. Expected energy we couldn't verify | **3,80,157 kWh** (shown separately) |

### By plant (34 days)
| | Plant 1 | Plant 2 |
|---|---|---|
| Actual energy | 52,87,949 kWh | 40,76,636 kWh |
| Expected energy | 52,87,779 kWh | 49,98,750 kWh |
| Performance ratio | **100%** | **82%** |
| Confirmed fault loss | 14,282 kWh | **9,13,398 kWh** |

The **worst inverter**: Plant 2, `LYwnQax7tkwH5Cb`: **80,807 kWh lost, 24 alerts.**

---

## 7.7 Step ⑦ — The energy waterfall (`engine/energy_breakdown.py`)

### The question
> "On a perfect day the plant could have made X. It actually made Y. **Where did the difference go?**"

### The waterfall, like a bucket with holes 🪣
Start with a full bucket (the best possible day) and see how much leaks out through each hole:

```
  Clear-sky potential       (what a clear sky + panels at 25 °C would give)
  − Clouds                  NATURAL  (nobody can fix the weather)
  − Heat                    NATURAL  (hot panels make less)
  − Faults                  FIXABLE  ← the red bar; this is where a technician helps
  − Not measured            UNKNOWN  (data gaps: we couldn't see)
  − Other                   small leftovers (model error, tiny issues below our thresholds)
  = Actual energy
```

**How each part is calculated:**
- **Cloud loss** = (clear-sky sunlight − actual sunlight) × the plant's kW per unit of sunlight at 25 °C.
- **Heat loss** = from Step ④.
- **Fault loss** = the confirmed losses from our alerts.
- **Not measured** = expected energy while an inverter was silent.
- **Other** = whatever is left. Because it's the leftover, **the parts always add up exactly** (a test checks this).

The order is logical: first how much sun arrived (clouds), then what the hot panels made of it (heat),
then what the equipment failed to deliver (faults). Each step starts from what's left, so nothing is
counted twice.

### Results (34 days)
| | Plant 1 | Plant 2 |
|---|---|---|
| Lost to clouds | 23,93,990 kWh (29.3%) | 19,84,014 kWh (25.6%) |
| Lost to heat | 4,92,219 kWh (6.0%) | 3,89,705 kWh (5.0%) |
| Lost to faults | 14,282 kWh (0.17%) | **9,13,398 kWh (11.8%)** |

**Both plants together: natural losses 52,59,927 kWh vs fixable losses 9,27,680 kWh.** The plants made
**58.8%** of their clear-sky potential.

> 🗣️ **The pitch line:** "Clouds and heat cost more, but **nobody can fix the weather**. The red bar,
> faults, is the part a technician can fix. **Operators should only chase the red bar.**"

---

## 7.8 Step ⑧ — Validation: proof it works (`engine/validate.py`, `engine/validate_weather.py`)

### The problem
There's **no official list** of "real faults" in the dataset (no **labels**). So how do we prove the
detector works?

### The solution: plant fake faults 🧪
**Like you're 5:** to test a smoke alarm, you hold a bit of smoke under it on purpose and check it beeps.

1. Take **healthy** inverter-days from the test period (no alerts at all).
2. **Break them on purpose**, with a fixed random seed so it's repeatable:
   - **Trip:** set output to 0 for 1–4 hours around noon.
   - **Underperformance:** multiply output by 0.6–0.85 for 2–6 hours.
   - **Data gap:** delete readings for 1–3 hours.
   - **Soiling:** a slow 0.3–1% per day decline.
3. Run the **exact same detector** with the **exact same thresholds**.
4. Count what was caught, missed, and falsely alarmed.

In total we planted **305 faults** (95 trips + 95 underperformance + 95 gaps + 20 soiling).

### Recall and precision: the fishing-net example 🎣
- **Recall** = of all the fish in the lake (real faults), **how many did the net catch?**
  `recall = caught ÷ planted`
- **Precision** = of everything in the net, **how much was fish, not old boots?** (boots = false alarms)
  `precision = real catches ÷ everything caught`

A huge net with tiny holes catches every fish (high recall) but also lots of boots (low precision).
That's the **trade-off**.

### Results
| Planted fault | Caught (recall) | False alarms | Time to alert |
|---|---|---|---|
| **Trip** | **100%** of 95 | 0 | ~32 min |
| **Data gap** | **100%** of 95 | 0 | 30 min |
| **Underperformance** | **71.6%** of 95 | 0 | ~71 min |
| **Soiling** | **80%** of 20 | 20 (precision 44.4%) | end of period |

**Honest about what we miss:**
- Small dips (the inverter still makes ≥ 80% of normal) are caught only **5.6%** of the time. That's **by
  design**: our rule needs at least 20% below, to avoid false alarms from clouds and noise.
- Very slow soiling (below 0.5% per day) over only 10 days isn't caught.
- "0 false alarms" is **optimistic**, because the healthy days were *chosen* as days with no alerts. We
  say this openly.

### The sensitivity trade-off
| Setting | Underperformance caught | False alarms |
|---|---|---|
| Sensitive | **98.9%** | **59** |
| Default (ours) | 71.6% | 0 |
| Strict | 24.2% | 0 |

More sensitive → catches more, but cries wolf more. We chose the middle.

### The weather-aware rule we tested, and switched OFF
Idea: under a cloudy, flickering sky, ask for **stronger proof** before raising an underperformance
alert.
- Result: false alarms **59 → 35** (better), **but 13 real planted faults were lost** (worse).
- Our rule was "keep it only if nothing real is lost", so **it's OFF** (`WEATHER_AWARE_UNDER = False`).
- Instead, every alert just **shows** the sky and a confidence level.
- Also tested: trips planted on cloudy days were caught **65 of 65**.

> 🗣️ "We'd rather show the operator an honest confidence level than hide real faults to make our numbers look nicer."

---

## 7.10 Tests (`tests/`)

**pytest** runs **104 automatic checks** (for example: "do the waterfall parts add up exactly?", "does a
planted trip get caught?", "does every API page answer?"). Run `pytest`; everything should pass. Tests
are like a checklist a pilot runs before take-off.

### ✅ Check yourself (Chapter 7)
1. What's "expected power"? → *What the inverter should make for this sunlight and temperature, predicted by the model.*
2. What's a Random Forest, in one sentence? → *100 decision-tree flowcharts each guess; we average their guesses.*
3. Why a time split and not a random split? → *To test on days the model never saw, like predicting the future from the past.*
4. Why is Plant 2's R² only 0.12 overall? → *Its many real outages count as model "errors", but those are exactly the faults. On healthy rows it's 0.84.*
5. What's the trip rule? → *Sunlight ≥ 0.25, output ≤ 1 kW, for 30+ minutes.*
6. Why compare with neighbours? → *A cloud dims everyone; a fault dims only one inverter.*
7. Lost energy formula? → *max(expected − actual, 0) × 0.25, added up over the alert.*
8. What's the difference between "lost" and "at risk"? → *Lost = we saw the shortfall. At risk = data gap, we couldn't see.*
9. Recall vs precision? → *Recall: how many real faults we caught. Precision: how many alarms were real.*
10. Why is the weather-aware rule off? → *It cut false alarms but lost 13 real faults.*

---

# Chapter 8 — The website, page by page

## 8.1 How the website gets its numbers (the restaurant 🍽️)

```
  WEBSITE (customer)  ──"Overview for Plant 2 on 27 May, please"──▶  API (waiter)
                                                                         │
                                                                         ▼
                                                         KITCHEN FILES (data/processed/*.parquet,
                                                                         reports/metrics.json)
  WEBSITE  ◀──────────── JSON answer (just numbers and text) ─────────── API
```

- The **engine** cooks everything **in advance** (`python run_all.py`).
- The **API** (FastAPI, `api/main.py` + `api/routes/`) only **reads** the files and returns **JSON**.
  (JSON is a simple text format for data, like `{"plant": 2, "loss_kwh": 51270}`.)
- The **website** (`web/`) only **displays** what the API sends. **It never calculates anything.**
- That's why the demo is fast and doesn't crash: no AI runs while you click.

**Start it locally:** `uvicorn api.main:app --reload`, then open http://localhost:8000.
**API playground:** http://localhost:8000/docs. FastAPI builds this page automatically, and you can
try every endpoint there.

**Online demo:** https://ojasguptaa.github.io/solarsense/. GitHub Pages can't run Python, so on every
push a robot (GitHub Actions) runs `python -m api.export_static`. That saves **every possible API answer**
as JSON files, and the website reads those instead (`web/js/mode.js` switches modes). The numbers are
identical. Only difference: Acknowledge / Resolve are saved in your own browser.

## 8.2 The API endpoints (the waiter's menu)

| Endpoint | What it answers |
|---|---|
| `GET /api/health` | "Is the engine alive?" |
| `GET /api/plants` | List of plants, dates, inverters |
| `GET /api/overview` | One plant on one day: takeaway sentence, KPI tiles, chart data, alerts needing attention |
| `GET /api/plant/timeseries` | Actual vs expected every 15 minutes |
| `GET /api/plant/daily` | Actual vs expected for every day |
| `GET /api/plant/heatmap` | The inverter × day health map |
| `GET /api/inverter/{id}` | One inverter: its power, neighbours, alerts |
| `GET /api/alerts` | The alert list (with filters) |
| `GET /api/alerts/{id}` | One alert with its "Why?" evidence |
| `POST /api/alerts/{id}/status` | Acknowledge / Resolve / Re-open an alert |
| `GET /api/losses` | Loss totals by plant, fault type, top inverters |
| `GET /api/validation` | The planted-fault proof |
| `GET /api/assumptions` | Every assumption, for the About page |
| `GET /api/settings` | Tariff and thresholds |
| `GET /api/replay` | Data for the "live replay" |
| `GET /api/weather/day`, `/weather/calendar`, `/weather/temperature` | Sky, calendar and heat data |
| `GET /api/breakdown` | The energy waterfall |

**GET** = "give me data". **POST** = "change something" (here: an alert's status).

## 8.3 Every page

Every page has: a top **navigation bar**, a **plant selector** (Plant 1 / Plant 2), a **date selector**,
and a **one-line takeaway** in plain English at the top. Colours: 🟢 OK, 🟠 warning, 🔴 critical. The
accent colour is solar amber. Little **ⓘ** icons explain assumptions.

### 🏠 Overview (`web/index.html`)
- **Shows:** the takeaway (e.g. *"14 inverters need attention — about 51,270 kWh lost, ₹1,53,809 at an
  assumed tariff"*), KPI tiles (big number + small comparison), the **actual (blue) vs expected (dashed)**
  chart for the plant, and the "Needs attention" alert list.
- **▶ Live replay:** plays a **recorded** day in 15-minute steps (speed 1×–4×). Alerts pop up as they
  would have in real life (from about 07:30 on Plant 2, 27 May).
- 🗣️ Always call it a **replay**. It's real recorded data, not a live feed.

### 🏭 Plant (`web/plant.html`)
- **Shows:** every day's actual vs expected, the **health map** (rows = inverters, columns = days,
  red = problem), and the worst inverters.
- 🗣️ "You can see Plant 2's trips aren't bad luck. They repeat day after day."

### 🌦️ Weather & Energy (`web/weather.html`)
- **Shows:** the sky band (☀️ ⛅ ☁️ 🌫️ through the day), sunlight vs the clear-sky curve, panel
  temperature, the **energy waterfall**, a calendar of all 34 days with sunshine scores, and "every
  +1 °C costs ~X% power".
- 🗣️ "Clouds and heat are natural. Only the red bar, faults, needs a technician."

### 🔌 Inverters (`web/inverter.html`)
- **Shows:** one inverter's day: actual vs expected vs **neighbours' median**, with alert periods
  **shaded red**, its daily trend, and its alerts.
- 🗣️ "The red area is the alert. Output is zero while its neighbours keep producing."

### 🚨 Alerts (`web/alerts.html`)
- **Shows:** all alerts. Filter by type/severity/status, search, sort, and **export to CSV** (opens in Excel).
- Click an alert → the **"Why?" panel**: reason sentence, evidence chart, numbers, sky, confidence,
  recommended action, **Acknowledge / Resolve / Re-open** buttons.
- 🗣️ "This is a work list, not just a chart."

### ℹ️ About (`web/about.html`)
- **Shows:** how it works, data sources and licences (Kaggle; NASA POWER is CC BY 4.0), every
  assumption, limitations, and the team.

The front-end code: `web/js/api.js` (shared "ask the API" helper), `web/js/charts.js` (Chart.js helpers),
and one small JS file per page (`overview.js`, `alerts.js`, …). Styling: `web/css/style.css`.

---

# Chapter 9 — Every library and tool, explained

**Library** = ready-made code that other people wrote and shared for free, so we don't have to write
everything from scratch. **Like you're 5:** LEGO sets. You don't make the bricks, you build with them.

| Library / tool | What it is, in one line | Analogy | Where we use it |
|---|---|---|---|
| **Python** | The programming language of our engine | The language the kitchen speaks | `engine/`, `api/` |
| **pandas** | Works with tables of data | "Excel, but in Python" | Everywhere in `engine/` |
| **numpy** | Fast maths on lots of numbers at once | A super calculator | Formulas, line fits |
| **pyarrow / Parquet** | Saves tables in a fast, small file format | A zip file made for tables | `data/processed/*.parquet` |
| **scikit-learn** | The machine-learning toolbox | A box of ready AI tools | `LinearRegression` (physics), `RandomForestRegressor`, `IsolationForest` |
| **joblib** | Saves a trained model to a file | A save-game file | `models/*.joblib` |
| **FastAPI** | Builds the web API | The waiter | `api/main.py`, `api/routes/` |
| **uvicorn** | The server that runs FastAPI | The restaurant building that opens the doors | `uvicorn api.main:app` |
| **pydantic** | Checks the shape of API answers | A form that must be filled in correctly | `api/schemas.py` |
| **pytest** + **httpx** | Run automatic tests | The pilot's checklist | `tests/` (104 tests) |
| **matplotlib** | Draws charts as PNG pictures | A drawing robot | `reports/figures/`, `presentation/figures/` |
| **HTML / CSS / JavaScript** | The website: structure / style / behaviour | Skeleton / clothes / muscles | `web/` |
| **Chart.js** | Draws interactive charts in the browser (loaded from a CDN) | Graph paper that draws itself | All website charts |
| **Git + GitHub** | Saves every version of the code and shares it online | Google Drive history for code | github.com/ojasguptaa/solarsense |
| **GitHub Actions + Pages** | A robot that rebuilds and hosts the website for free on every push | A free robot publisher | `.github/workflows/pages.yml` |

**Why these choices?** Everything is **free, open-source, needs no API keys**, and runs on a normal
8 GB laptop. No React, no build tools: plain HTML/JS keeps it simple and easy to explain.

**Random seed 42:** "random" steps (Random Forest, planted faults, bootstrap) use a fixed seed, so every
run gives **exactly the same results**. This is called **reproducibility**.

---

# Chapter 10 — Case studies from our own data

Stories stick better than numbers. Learn these 6.

## 📖 Case 1: Plant 2's worst day (27 May 2020)
- **The situation:** the takeaway reads *"14 inverters need attention — about 51,270 kWh lost, ₹1,53,809
  at an assumed tariff."* The plant made only **68%** of what the weather allowed.
- **The biggest alert, `P2-TRIP-0126`:** output **0 kW for 7.75 hours** while sunlight was strong;
  about **952 kW** was expected; **7,382 kWh** lost.
- **Without SolarSense:** someone notices at the end of the month.
- **With SolarSense:** the alert pops up after about **30 minutes** with a reason and an action ("send a technician").
- **The waterfall that day:** clouds cost 19,917 kWh and heat 17,814 kWh (natural), but **faults cost
  51,270 kWh** (fixable). Faults were the **biggest** loss of the day.

## 📖 Case 2: "It wasn't the weather" (Plant 2, 15 May)
- The sky was **clear** (sunshine score 96, almost all yellow in the sky band).
- But at midday the power line goes flat, far below what the sun allowed.
- Clouds cost 11,366 kWh and heat 16,104 kWh. **Faults cost 38,049 kWh.**
- **Lesson:** SolarSense **removes the excuse** "it was cloudy". Send a technician.

## 📖 Case 3: A big loss with nothing to fix (Plant 2, 11 June)
- Sunshine score **38** ☁️, a cloudy day.
- Clouds cost **1,42,478 kWh**. Faults cost **0**.
- **Lesson:** a big loss isn't always a problem. SolarSense stops operators from **chasing clouds**.

## 📖 Case 4: The worst inverter
- Plant 2, `LYwnQax7tkwH5Cb`: **80,807 kWh lost, 24 alerts** in 34 days, mostly trips.
- That's about ₹2.4 lakh at ₹3/kWh from **one** box.
- **Lesson:** a repeat offender. Investigate or replace it, rather than restarting it every day.

## 📖 Case 5: A healthy plant vs a sick plant
| | Plant 1 | Plant 2 |
|---|---|---|
| Actual ÷ expected | **100%** | **82%** |
| Fault loss | 14,282 kWh | 9,13,398 kWh |
| Inverters with alerts | 11 of 22 | 22 of 22 |
- **Lesson:** both plants had similar weather, but Plant 2 lost **64 times** more energy to faults.
  Weather didn't cause that; **equipment** did. That's exactly what SolarSense is built to reveal.

## 📖 Bonus: why this matters at scale (a hypothetical example; say "for example")
*This uses made-up round numbers to show the arithmetic. It isn't from our data.*
- Imagine a **50 MW** plant with 25 inverters of **2 MW** each.
- One inverter trips on a sunny morning and nobody notices. A sunny day gives about 5.5 "full-sun
  hours", so it loses about 2,000 kW × 5.5 h ≈ **11,000 kWh per day**.
- At ₹3/kWh that's ≈ **₹33,000 per day**.
- Found after **30 days** (the monthly report) → ≈ **₹10 lakh** lost.
- Found after **30 minutes** (SolarSense) → only the energy from those 30 minutes, about ₹3,000 if it is
  fixed right away (2,000 kW × 0.5 h × ₹3).

---

# Chapter 11 — How our product helps

## 11.1 Before vs after, for the operator

| Before SolarSense | With SolarSense |
|---|---|
| Faults found at the end of the month | Alert in about **30 minutes** (trips) |
| "Output is low", but is it a cloud or a fault? | Compared with expected **and** neighbours, plus the sky shown on every alert |
| "Something's wrong somewhere" | **Which** inverter, **when**, **why**, **what to do** |
| Loss unknown | Loss in **kWh and ₹** on every alert |
| All losses look the same | **Natural** (clouds, heat) vs **fixable** (faults) waterfall |
| A wall of alarms | Sorted by severity and loss, with a confidence level |
| No proof the alarms are right | Injected-fault test: what we catch **and what we miss** |

## 11.2 Competitive advantage

| | Basic SCADA alarm | Notebook analysis | **SolarSense** |
|---|---|---|---|
| Knows what output *should* be for the weather | ✗ | sometimes | **✓** |
| Explains each alert in plain words | ✗ | ✗ | **✓** |
| Loss in kWh and ₹ per alert | ✗ | rarely | **✓** |
| Validated detection rate, including what it misses | ✗ | ✗ | **✓** |
| Separates weather losses from fixable losses | ✗ | rarely | **✓** |
| Operator workflow (acknowledge / resolve / export) | partly | ✗ | **✓** |

*SCADA* = the basic control-room software most plants already have. It usually raises an alarm only
on simple limits (e.g. "power = 0"). It doesn't know what the power **should** be.

## 11.3 Honest limitations (say these before a judge does)
1. Only **34 days**, one season (May–June). We don't know winter or monsoon accuracy.
2. **One weather sensor** per plant (peer comparison helps).
3. **No labelled faults**, so we used planted faults to validate.
4. The **tariff is assumed** (₹3/kWh).
5. Small dips (under 20%) are mostly missed **on purpose**.
6. Overheating can only be judged plant-wide.
7. **Replay**, not live data, in the demo.
8. Not benchmarked on 1,000 inverters (the full rebuild takes about 97 s for 44 inverters × 34 days on a laptop).

## 11.4 Roadmap
- A live 15-minute data feed + email/SMS alerts.
- More seasons of data → better accuracy all year.
- String-level data → pinpoint the exact string.
- The plant's GPS → a physical clear-sky model instead of our learned curve.

---

# Chapter 12 — About Meridian, the judges' company

## 12.1 What we could confirm (October 2026)

From Meridian's own website, **onmeridian.com**:
- It describes itself as a **"Next-Gen Enterprise Cloud & AI Infrastructure Platform"**.
- What it does: helps **high-growth engineering teams**
  - **orchestrate multi-cloud infrastructure**: run software across several cloud providers (AWS,
    Azure, Google Cloud…) from one place,
  - **automate zero-trust compliance**: "zero trust" means *never automatically trust any user or
    device, always verify*. Compliance means following the security rules,
  - **optimise AI compute workloads**: make AI jobs run efficiently on expensive hardware (GPUs) and
    not waste money.
- Listed features: **cloud orchestration, AI-driven auto-scaling, continuous zero-trust security**.

**Like you're 5:** Meridian is like a very smart building manager for computers in the cloud. It makes
sure the right number of computers are switched on (auto-scaling), every door has a security check
(zero trust), and the expensive AI machines aren't wasted.

## 12.2 What we could NOT find, and what to do about it

⚠️ We searched, and **leadership names (CEO/founder), founding year, headquarters and past projects
are not publicly listed** in any source we could find. The name "Meridian" is also used by several
**unrelated** companies (Meridian Energy in New Zealand, Meridian Solar in Texas, other "Meridian" AI
startups). **Don't mix them up, and don't say a CEO's name on stage unless you've confirmed it.**

**Before the event, check (10 minutes):**
- [ ] The onmeridian.com **About / Team** page (open it in a normal browser; it may load content that our tools couldn't read).
- [ ] Meridian's **LinkedIn** company page → "People" for the CEO/founders.
- [ ] The **hackathon portal / problem statement PDF / emails** from the organisers. They often name the judges and the company's goals.
- [ ] Write what you find here: CEO: ________ Founded: ________ HQ: ________ Known projects: ________

If a judge asks "do you know about our company?", a safe, honest answer:
> "From your site, Meridian builds a cloud and AI infrastructure platform: multi-cloud orchestration,
> zero-trust security and AI compute optimisation. Our project shares that spirit: it uses AI to watch
> a fleet of machines, compare what they *should* do with what they *actually* do, and act early."

## 12.3 How SolarSense connects to Meridian's world (talking points)

1. **Same core idea: monitoring a fleet.** Meridian watches cloud servers and AI workloads; SolarSense
   watches inverters. Both compare **expected vs actual** and flag problems early. In cloud language
   this is **observability** and **anomaly detection**. Our method would carry straight over to servers.
2. **Auto-scaling ↔ expected output.** Auto-scaling predicts how much compute you *need*. Our model
   predicts how much power you *should* get. Both are **prediction + action**.
3. **Explainable AI.** Enterprise teams don't trust black boxes. Every SolarSense alert has a reason,
   evidence and a confidence level, and the AI never decides alone.
4. **Cloud-ready architecture.** Precomputed pipeline → stateless JSON API → static front-end. It runs
   on a laptop, a free host, or any cloud, and scales by adding plants, not rewriting code.
5. **Honest numbers = trust (a "zero-trust" mindset for data).** We didn't trust the raw data blindly:
   we verified it, found Plant 1's 10× DC error, and labelled every assumption.
6. **Energy for AI.** AI data centres use a lot of electricity, and many are moving to solar power.
   Keeping solar plants healthy helps power AI cleanly. *(General point; don't quote figures without a source.)*

---

# Chapter 13 — Presentation kit

## 13.1 The 60-second pitch
See Chapter 0. Learn it word for word.

## 13.2 The 3-minute pitch (structure)
1. **Problem (20 s):** "Solar operators learn about broken inverters only after losses pile up. In our
   data alone, faults cost **9,27,680 kWh in 34 days**, about ₹27.8 lakh at an assumed ₹3/kWh."
2. **Idea (20 s):** "We compare what every inverter **made** with what it **should** have made for the weather."
3. **How (40 s):** "An AI model learns expected output from sunlight and temperature. 96% R² on unseen
   days, and a physics formula agrees. Clear rules plus neighbour comparison flag 6 fault types, each
   with a reason, kWh and ₹ lost, and an action."
4. **Weather (20 s):** "We read the sky from the sunlight itself and split losses into natural and
   fixable. Operators chase only the red bar."
5. **Proof (20 s):** "We planted 305 faults: trips and data gaps 100% caught, underperformance 71.6%,
   and we show what we miss."
6. **Demo (40 s):** Overview → replay → alert "Why?" → inverter page.
7. **Close (10 s):** "SolarSense finds losses in minutes, explains them, and puts a rupee value on them."

## 13.3 Slides ↔ chapters
| Slide (`slide_outline.md`) | Learn it from |
|---|---|
| 1–2 Problem, cost | Chapters 4, 5 |
| 3 Solution picture | Chapter 7.0 |
| 4 How the AI works | Chapters 7.2, 7.3, 7.5 |
| 5 Demo | Chapter 8, `demo_script.md` |
| 6 Proof | Chapter 7.8 |
| 7 Money | Chapters 4, 7.6 |
| 8 Weather | Chapters 3, 7.7 |
| 10 Competitive advantage | Chapter 11 |
| 11 Roadmap | Chapter 11.4 |

## 13.4 The 2-minute demo (short version; full version in `demo_script.md`)
1. **Overview**, Plant 2, **27 May** → read the takeaway line.
2. Point at the tiles: "only **68%** of what the weather allowed."
3. Speed **4×** → **▶ Live replay** → alerts pop up: "we'd know within about half an hour."
4. Click **P2-TRIP-0126** → read the reason: 0 kW for 7.75 h, ~952 kW expected, 7,382 kWh lost, action.
5. **Acknowledge** → "it's a work list."
6. Inverter link → "red area = alert; neighbours keep producing."
7. **Plant** health map → "the trips repeat."
8. **Validation** → "305 planted faults: trips and gaps 100%."
9. After the demo: **Re-open** the alert.

**Backup:** screenshots in `presentation/figures/` (order 1 → 2 → 4 → 3 → 5). Open the site 2 minutes early.

## 13.5 Top judge questions in super-simple words
(The full 27 are in `judge_qa.md`.)

| Question | Your simple answer |
|---|---|
| "Is 34 days enough?" | "Enough to prove the method, not enough for all seasons. More seasons is our first roadmap item." |
| "How do you know it works without labels?" | "We planted 305 faults ourselves, like testing a smoke alarm with smoke. Trips: 100% caught." |
| "Why is Plant 2's R² 0.12?" | "Its many real outages count as 'errors', but they're the faults we catch. On healthy readings it's 0.84." |
| "Cloud or fault, how can you tell?" | "A cloud dims all 22 inverters together. A fault dims one. We compare each inverter with its neighbours." |
| "Where's the ₹3 from?" | "It's an assumption, labelled everywhere and configurable. Change one number and every ₹ updates." |
| "Why not let AI decide everything?" | "Operators need a reason and an action. Rules give both; the AI gives the expected value." |
| "Is this live?" | "It's a replay of real recorded data. Live 15-minute feeds are the next step." |
| "Did AI write your code?" | "Yes, we used Claude Code to write most of it, phase by phase. We set the goals and rules, approved every plan, checked results, chose thresholds, and can explain every part." |
| "Biggest limitation?" | "34 days in one season, one weather sensor per plant, and an assumed tariff." |
| "Why Random Forest if physics is as good?" | "They're nearly equal, and that's a feature: the physics formula proves our AI learned real physics, not a trick." |

## 13.6 ❌ What NOT to say
- ❌ "Live data" → ✅ "a **replay** of recorded data".
- ❌ "The plants are in Gujarat/Rajasthan/…" → ✅ "the dataset doesn't include location".
- ❌ "We lose ₹2.99 crore a year" as a fact → ✅ "an **estimate**, scaled from 34 days, at an assumed tariff".
- ❌ "100% accurate" → ✅ "trips and gaps were 100% caught **in our planted-fault test**; underperformance 71.6%".
- ❌ "₹3/kWh is the real tariff" → ✅ "an **assumed** tariff".
- ❌ Any national statistic (India's solar capacity, etc.) without a source you can name.
- ❌ A Meridian CEO name you haven't confirmed.
- ❌ Mixing up **kW** (power, right now) and **kWh** (energy, total).

---

# Chapter 14 — Glossary and formula cheat-sheet

## 14.1 Glossary (A–Z)

| Term | Simple meaning |
|---|---|
| **AC (Alternating Current)** | Electricity that flips direction back and forth (wall socket, grid) |
| **Alert** | A detected fault event with type, inverter, time, severity, reason, loss, action, status |
| **Ambient temperature** | Air temperature |
| **API** | The "waiter" between the website and the engine's data |
| **ASSUMPTION** | A number we had to choose rather than measure. Labelled everywhere |
| **At-risk energy** | Expected energy during a data gap. Not counted as lost |
| **Baseline** | A simple model used for comparison (our physics formula) |
| **Bootstrap** | Refitting many times on random re-draws of the data to see how much an answer wobbles |
| **Capacity** | A plant's maximum power (kW/MW): its "size" |
| **Clear-sky index (CSI)** | Actual sunlight ÷ clear-sky sunlight. 1 = clear, below 0.3 = overcast |
| **Confidence** | How sure we are about an alert (High / Medium / Low) |
| **DC (Direct Current)** | Electricity flowing one way (battery, solar panel) |
| **Data gap** | Missing readings during daylight |
| **Degradation / soiling** | A slow decline in output (dust, ageing) |
| **Expected power** | What an inverter **should** make for this weather (model output) |
| **Feature** | An input the model looks at (sunlight, temperature…) |
| **Feature importance** | How much each input mattered to the model |
| **Inverter** | The box that turns DC into AC. Our unit of monitoring |
| **Irradiation / irradiance** | Sunlight strength (kW/m², about 1.0 at a sunny noon) |
| **Isolation Forest** | An AI method that finds unusual data points (a hint only) |
| **JSON** | A simple text format for sending data |
| **kW** | Power: how fast energy flows right now |
| **kWh** | Energy: power × time. 1 kWh = 1 "unit" on a bill |
| **Labels** | The "correct answers" in data (we have none for faults) |
| **MAE** | Average error in kW |
| **MAPE** | Average error in % |
| **Median** | The middle value when sorted. Not fooled by extremes |
| **Module** | A solar panel |
| **Module temperature** | The panel's own temperature |
| **NASA POWER** | Free NASA satellite sunlight/temperature data |
| **O&M** | Operations & Maintenance: the people who fix the plant |
| **Parquet** | A fast, compact file format for tables |
| **Peer comparison / peer ratio** | My performance ÷ the median of all inverters at the same moment |
| **Performance ratio (PR)** | Actual energy ÷ expected energy |
| **Physics formula** | expected ≈ k × sunlight × (1 − γ × (temp − 25)) |
| **Pipeline** | All engine steps run in order (`run_all.py`) |
| **Precision** | Of the alarms raised, how many were real |
| **R²** | Share of the ups and downs the model explains (1 = perfect) |
| **Random Forest** | Many decision trees whose guesses are averaged |
| **Recall** | Of the real faults, how many we caught |
| **Replay** | Playing recorded data back as if it were live |
| **Residual** | Actual − expected |
| **Seed (42)** | A fixed starting point for randomness, so results repeat exactly |
| **Severity** | How bad an alert is, by energy lost |
| **SOURCE_KEY** | The inverter's ID in the data |
| **Specific yield** | kWh per year per kW of capacity |
| **STC (25 °C)** | Standard Test Conditions, where panels are rated |
| **String** | A line of panels wired together |
| **Sunshine score** | A day's sunlight as % of the clear-sky curve |
| **Tariff** | Price per kWh (₹/kWh) |
| **Temperature coefficient** | % power lost per °C above 25 °C (ours: −0.392 %/°C) |
| **Test set / training set** | Days used to check / to teach the model |
| **Time split** | Train on earlier days, test on later ones (never random) |
| **Trip** | The inverter switches off while the sun shines |
| **Underperformance** | Clearly below expected and below neighbours |
| **Validation** | Proving the detector works (planted faults) |
| **Variability** | How much the sunlight flickers (passing clouds) |
| **Waterfall** | A breakdown of where energy went: clouds, heat, faults, not measured, other |

## 14.2 📋 Formula cheat-sheet (one screen)

```
ENERGY
  energy (kWh)          = power (kW) × time (h)
  one 15-min reading    = power (kW) × 0.25
  readings per day      = 96

MONEY
  money (₹)             = energy (kWh) × tariff (₹/kWh)        ← tariff = ₹3 (ASSUMPTION)
  yearly projection     = 34-day loss × 365 ÷ 34                ← ESTIMATE

PERFORMANCE
  performance ratio     = actual energy ÷ expected energy
  residual (kW)         = actual − expected
  residual (%)          = 100 × (actual − expected) ÷ expected  (only when expected ≥ 50 kW)
  peer ratio            = (my actual ÷ my expected) ÷ median of everyone's (actual ÷ expected)
  specific yield        = kWh per year ÷ kW capacity

MODEL
  physics               : expected ≈ k × irradiation × (1 − γ × (module_temp − 25))
                          Plant 1: k = 1,453.28 kW, γ = 0.0041 /°C
  random forest         : average of 100 decision trees on 5 features

LOSS
  lost energy           = Σ max(expected − actual, 0) × 0.25   (over the alert)

WEATHER
  clear-sky index       = actual sunlight ÷ clear-sky sunlight (95th percentile of 34 days, smoothed)
  heat loss %           = |coefficient| × (panel temp − 25)     (Plant 1: 0.392 %/°C)
  power at 25 °C        = expected ÷ (1 − heat share lost)

WATERFALL
  actual = clear-sky potential − clouds − heat − faults − not measured − other

FAULT RULES (defaults)
  trip                  : sunlight ≥ 0.25 AND output ≤ 1 kW, for ≥ 30 min
  underperformance      : ≥ 20% below expected AND ≥ 20% below neighbours, for ≥ 1 h
  data gap              : no readings in daylight, for ≥ 30 min
  degradation           : relative PR falls ≥ 0.3 %/day AND ≥ 5% total, over ≥ 10 days
  overheating           : panel ≥ 28 °C above air AND plant < 90% of expected, for ≥ 30 min
  severity              : ≥ 2,000 kWh Critical · ≥ 500 High · ≥ 100 Medium · else Low (+1 level if ≥ 4 h)

VALIDATION
  recall                = caught ÷ planted
  precision             = real alarms ÷ all alarms

```

## 14.3 🔢 The 15 numbers to know by heart

| # | Number | What it is |
|---|---|---|
| 1 | **2 plants, 22 inverters each, 34 days, every 15 min** | The data |
| 2 | **10.001×** | Plant 1 DC error we fixed |
| 3 | **0.96** | Plant 1 model R² on unseen days |
| 4 | **98.7%** | Sunlight's share of the model's decisions (Plant 1) |
| 5 | **429** | Alerts in total (358 trips) |
| 6 | **9,27,680 kWh** | Energy lost to faults (34 days) |
| 7 | **₹27.8 lakh** | That in money at the assumed ₹3/kWh |
| 8 | **82%** | Plant 2's actual vs expected (Plant 1: 100%) |
| 9 | **99%** | Share of lost energy caused by trips |
| 10 | **305** | Faults we planted to test ourselves |
| 11 | **100% / ~32 min** | Trips caught / time to alert |
| 12 | **71.6%** | Underperformance caught |
| 13 | **−0.39 %/°C** | Power lost per °C (Plant 1, measured) |
| 14 | **52.6 lakh vs 9.3 lakh kWh** | Natural vs fixable losses |
| 15 | **1,271 / 1,413 / 1,387** | kWh per kW per year: Delhi / Jaipur / Chennai |

---

# Chapter 15 — Final self-test

Cover the answers, say yours out loud, then check. If you get 20+ right, you're ready. 🎉

1. **What's the difference between kW and kWh?**
   → kW is power right now (speed); kWh is energy in total (distance). kWh = kW × hours.
2. **An inverter makes 1,000 kW for one 15-minute reading. How much energy?**
   → 1,000 × 0.25 = 250 kWh.
3. **What does an inverter do and why do we monitor it?**
   → It turns DC from the panels into AC for the grid. If it fails, every panel behind it is wasted, and our data is per inverter.
4. **What's irradiation?**
   → Sunlight strength, about 1.0 kW/m² at a sunny noon, 0 at night.
5. **Why do hot panels matter?**
   → They make less power, about 0.39% less per °C above 25 °C on our Plant 1.
6. **How did you find Plant 1's data was wrong?**
   → AC ÷ DC was 9.8%, which is impossible (Plant 2: 97.9%). The DC was about 10× too big, so we divided by 10.001 and labelled it ASSUMPTION.
7. **Do you fill in missing readings?**
   → No. Gaps stay visible and become data-gap alerts. Their energy is "at risk", not "lost".
8. **What is "expected output"?**
   → What an inverter should make for the current sunlight and temperature, predicted by our model.
9. **Explain a Random Forest to a child.**
   → 100 flowcharts each guess; we average the guesses, like averaging 100 friends' guesses of sweets in a jar.
10. **How did you test the model fairly?**
    → Trained on the first 24 days and tested on the last 10 unseen days. A time split, never random.
11. **What does R² 0.96 mean?**
    → The model explains 96% of the ups and downs in power on unseen days.
12. **Why does Plant 2 have R² 0.12?**
    → Many real outages count as model "errors", but they're the faults we detect. On healthy rows it's 0.84.
13. **How do you tell a cloud from a fault?**
    → A cloud dims all inverters together; a fault dims one. We compare each inverter with the median of its neighbours.
14. **What's the trip rule?**
    → Sunlight ≥ 0.25 and output ≤ 1 kW for at least 30 minutes.
15. **What's the underperformance rule?**
    → At least 20% below expected and at least 20% below neighbours, for at least 1 hour.
16. **How do you calculate lost energy and money?**
    → Add up max(expected − actual, 0) × 0.25 over the alert; × ₹3/kWh (assumed) for money.
17. **How much was lost to faults in total?**
    → 9,27,680 kWh in 34 days, about ₹27.8 lakh at the assumed tariff; 99% from trips.
18. **How do you know the sky was cloudy with no cloud sensor?**
    → Clear-sky index: actual sunlight ÷ a clear-sky curve learned from the brightest days at each time of day.
19. **What does the waterfall show?**
    → Clear-sky potential minus clouds, heat (natural), faults (fixable), not measured and other = actual. Operators chase only the fixable part.
20. **How did you validate fault detection without labels?**
    → We planted 305 faults into healthy data and ran the same detector: trips and gaps 100%, underperformance 71.6%, soiling 80%.
21. **Recall vs precision?**
    → Recall: share of real faults caught. Precision: share of alarms that were real.
22. **Why is the weather-aware rule switched off?**
    → It cut false alarms from 59 to 35 but lost 13 real planted faults. We don't trade real faults for fewer alarms.
    → It uses free NASA satellite sunlight and temperature for any place in India to estimate monthly energy, with our measured heat effect. Planning only, about ±10%.
24. **What happens when I click a page on the website?**
    → JavaScript asks the API; the API reads precomputed files and returns JSON; the page draws it with Chart.js. No AI runs during clicks.
25. **What does Meridian do?**
    → From its website: an enterprise cloud and AI infrastructure platform: multi-cloud orchestration, zero-trust security, AI compute optimisation. (Confirm leadership details yourself before the event.)
26. **What's your biggest limitation?**
    → 34 days in one season, one weather sensor per plant, no fault labels, and an assumed tariff.
27. **Say the 60-second pitch.**
    → (Chapter 0.)

---

> 💛 **Last words:** you don't need to know everything. When you don't know, say: *"We didn't measure
> that, but here's what we did measure…"*. Judges respect honesty much more than guessing. You built
> something real, tested it honestly, and now you understand it. **Go show them.** 🌞

*Numbers in this guide come from `reports/metrics.json` and `presentation/key_numbers.md` (pipeline
outputs). If you re-run `python run_all.py` after changing a setting (for example the tariff), re-check
the numbers in `key_numbers.md`.*
