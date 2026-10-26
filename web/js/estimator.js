// Solar Site Planner page (Phase 12): expected energy per month for a new plant anywhere in India, from free
// NASA POWER weather. The API does all the maths — this page only sends the inputs and draws the answer.

const STATIC_ESTIMATOR_NOTE = "Static demo copy: only the example cities are saved here. "
  + "To try any location, run SolarSense locally (uvicorn api.main:app).";
let siteSetup = null;
let lastEstimate = null;

const field = (id) => document.getElementById(id);

function setStatus(message, isError = false) {
  const status = field("site-status");
  status.textContent = message;
  status.classList.toggle("error", isError);
}

/** Fill the form with one example city and estimate it right away. */
function choosePreset(city) {
  field("site-lat").value = String(city.lat);
  field("site-lon").value = String(city.lon);
  field("site-capacity").value = String(siteSetup.default_capacity_kw);
  document.querySelectorAll("#presets button").forEach((button) =>
    button.setAttribute("aria-pressed", String(button.dataset.city === city.name)));
  runEstimate(city.name);
}

/** Check the inputs in plain words (the API checks them again). Returns an error message or "". */
function inputProblem(lat, lon, capacity) {
  const [latMin, latMax] = siteSetup.lat_range, [lonMin, lonMax] = siteSetup.lon_range;
  if ([lat, lon, capacity].some((value) => Number.isNaN(value))) return "Please fill in all three numbers.";
  if (lat < latMin || lat > latMax || lon < lonMin || lon > lonMax)
    return `Please choose a place in India (latitude ${latMin}–${latMax}, longitude ${lonMin}–${lonMax}).`;
  if (capacity <= 0) return "Plant size must be more than 0 kW.";
  return "";
}

async function runEstimate(cityName = null) {
  const raw = { lat: field("site-lat").value, lon: field("site-lon").value, capacity_kw: field("site-capacity").value };
  const problem = inputProblem(Number(raw.lat), Number(raw.lon), Number(raw.capacity_kw));
  if (problem) { setStatus(problem, true); return; }
  if (!cityName) document.querySelectorAll("#presets button").forEach((b) => b.setAttribute("aria-pressed", "false"));
  setStatus("Asking NASA POWER for a year of weather… (up to 10 seconds)");
  field("site-go").disabled = true;
  try {
    lastEstimate = await fetchJSON("/api/site-estimate", raw);
    renderEstimate(lastEstimate, cityName);
    setStatus(STATIC_SITE ? STATIC_ESTIMATOR_NOTE
      : `Weather data: ${lastEstimate.data_from}, ${fmt.date(lastEstimate.period_start)} – ${fmt.date(lastEstimate.period_end)}.`);
  } catch (error) {
    setStatus(error.message.replace(/<[^>]+>/g, ""), true);   // plain text: the message may contain <code>
  } finally {
    field("site-go").disabled = STATIC_SITE;
  }
}

function renderEstimate(data, cityName) {
  const place = cityName || `${data.lat}°N, ${data.lon}°E`;
  field("takeaway").textContent = data.takeaway;
  const tile = (label, value, compare, tip = "") => `<div class="card kpi">
      <div class="kpi-label">${label}${tip ? infoTip(tip) : ""}</div><div class="kpi-value">${value}</div>
      <div class="kpi-compare">${compare}</div></div>`;
  field("kpis").innerHTML = [
    tile("Energy per year", `${fmt.number(data.yearly_kwh)}<span class="unit">kWh</span>`,
      `${fmt.number(data.capacity_kw)} kW plant at ${escapeHTML(place)}`),
    tile("Per kW of panels", `${fmt.number(data.specific_yield_kwh_per_kw)}<span class="unit">kWh/kW</span>`,
      "per year, flat panels", "ASSUMPTION: panels lie flat. Tilting them towards the sun usually gives more."),
    tile("Best / lowest month", `${escapeHTML(data.best_month.slice(0, 3))} / ${escapeHTML(data.worst_month.slice(0, 3))}`,
      `${escapeHTML(data.best_month)} vs ${escapeHTML(data.worst_month)}`),
    tile("Hot panels cost", `${fmt.number(data.heat_loss_pct, 1)}<span class="unit">%</span>`,
      "of the year's energy vs panels at 25 °C", "Uses the temperature effect we measured on our Kaggle plant."),
  ].join("");
  field("site-chart-title").textContent = `Expected energy per month — ${place}`;
  drawSiteChart(data.months);
  field("site-assumptions").innerHTML = data.assumptions.map((a) => `<tr><td>${escapeHTML(a.name)}</td>
      <td>${fmt.number(a.value, Number.isInteger(a.value) ? 0 : 2)} ${escapeHTML(a.unit)}</td>
      <td>${escapeHTML(a.source)}</td></tr>`).join("");
  field("site-note").textContent = data.uncertainty_note
    + (data.days_missing ? ` ${data.days_missing} days had no NASA value and were filled with their month's average.` : "");
}

function drawSiteChart(months) {
  Charts.draw("site-chart", {
    type: "bar",
    data: {
      labels: months.map((m) => m.label),
      datasets: [
        { type: "line", label: "Panel temperature (°C)", data: months.map((m) => m.panel_temp_c), yAxisID: "temp",
          borderColor: Charts.color("--high"), backgroundColor: Charts.color("--high"), borderWidth: 2,
          pointRadius: 3, tension: 0.3 },
        { label: "Expected energy (kWh)", data: months.map((m) => m.expected_kwh), yAxisID: "energy",
          backgroundColor: Charts.color("--chart-expected"), borderRadius: 3 },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: {
        x: Charts.axis("Month", { ticks: { maxRotation: 0, autoSkip: true } }),
        energy: Charts.axis("Expected energy (kWh)", { position: "left", beginAtZero: true }),
        temp: Charts.axis("Panel temperature (°C)", { position: "right", grid: { drawOnChartArea: false } }),
      },
      plugins: { tooltip: { callbacks: {
        label: (ctx) => (ctx.dataset.yAxisID === "temp" ? `Panel temperature: ${fmt.number(ctx.parsed.y, 1)} °C`
          : `Expected: ${fmt.kwh(ctx.parsed.y)}`),
        afterBody: (items) => { const m = months[items[0].dataIndex];
          return [`Sunlight: ${fmt.number(m.sunlight_kwh_m2_day, 2)} kWh/m² per day`,
            `Air (24 h average): ${fmt.number(m.air_temp_c, 1)} °C`]; },
      } } },
    },
  });
}

/** The "How accurate is this?" card: backtest on our plant, PVGIS cross-check, year-to-year spread. */
function renderAccuracy(acc) {
  if (!acc || !acc.summary) return;   // checks not run yet (python -m engine.validate_site)
  const back = acc.backtest, cities = Object.entries(acc.cities);
  const signed = (value) => `${value > 0 ? "+" : ""}${fmt.number(value, 1)}%`;
  const fact = (label, value, compare, tip) => `<div class="card kpi"><div class="kpi-label">${label}${infoTip(tip)}</div>
      <div class="kpi-value">${value}</div><div class="kpi-compare">${compare}</div></div>`;
  const spreads = cities.map(([, c]) => c.year_spread_pct);
  field("acc-facts").innerHTML = [
    fact("Backtest: error per day", `${fmt.number(back.planner.daily_error_pct, 1)}<span class="unit">%</span>`,
      `${back.test_days} unseen days on Plant ${back.plant} · without the heat effect: ${fmt.number(back.sunlight_only.daily_error_pct, 1)}%`,
      `We gave the method Plant ${back.plant}'s real daily sunlight and air temperature, tuned only the plant size on `
      + `the first ${back.train_days} clean days, and predicted the last days (${back.test_period}).`),
    fact("Backtest: total energy", signed(back.planner.total_error_pct), `over ${back.test_days} unseen days`,
      "Predicted minus real energy, added up over the test days."),
    fact("Weather year to year", `≤ ${fmt.number(Math.max(...spreads), 1)}<span class="unit">%</span>`,
      "change in a year's energy, 2021–2025", "Highest minus lowest year, as a share of the average year."),
  ].join("");
  field("acc-cities").innerHTML = cities.map(([name, c]) => {
    const years = Object.values(c.yearly_yield_kwh_per_kw);
    return `<tr><td>${escapeHTML(name)}</td>
      <td>${fmt.number(c.pvgis.yield_kwh_per_kw)} kWh/kW</td><td>${fmt.number(c.ours_yield_kwh_per_kw)} kWh/kW</td>
      <td><strong>${signed(c.total_gap_pct)}</strong></td><td>${signed(c.sunlight_gap_pct)}</td>
      <td>${signed(c.maths_gap_pct)}</td>
      <td>${fmt.number(Math.min(...years))}–${fmt.number(Math.max(...years))} kWh/kW</td></tr>`;
  }).join("");
  const first = cities[0][1];
  field("acc-summary").textContent = `${acc.summary} PVGIS uses ${first.pvgis.weather_data} weather; ours uses `
    + `${first.ours_years} (average year). ${acc.pvgis_note}`;
  field("accuracy").hidden = false;
}

async function initEstimator() {
  await Layout.init("estimator");
  try {
    siteSetup = await fetchJSON("/api/site-estimate/presets");
  } catch (error) {
    showError(error.message);
    return;
  }
  field("presets").innerHTML = siteSetup.presets.map((city, index) =>
    `<button type="button" data-index="${index}" data-city="${escapeHTML(city.name)}" aria-pressed="false">
       ${escapeHTML(city.name)}</button>`).join("");
  field("presets").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (button) choosePreset(siteSetup.presets[Number(button.dataset.index)]);
  });
  field("site-form").addEventListener("submit", (event) => { event.preventDefault(); runEstimate(); });
  if (STATIC_SITE) {   // no server to ask NASA: only the saved example cities work
    ["site-lat", "site-lon", "site-capacity", "site-go"].forEach((id) => { field(id).disabled = true; });
  }
  renderAccuracy(siteSetup.accuracy);
  window.addEventListener("themechange", () => { if (lastEstimate) drawSiteChart(lastEstimate.months); });
  choosePreset(siteSetup.presets[0]);
}

initEstimator();
