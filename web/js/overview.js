// Overview page: takeaway, KPI tiles, actual-vs-expected chart, alerts needing attention, loss by fault type.

let lastData = null;   // kept so charts can be redrawn when the theme changes

async function loadOverview(state) {
  const { plant, date } = state;
  if (typeof Replay !== "undefined") Replay.stop(false);   // a new plant/date ends any running replay
  document.getElementById("all-alerts-link").href = `alerts.html?plant=${plant}`;
  try {
    const [overview, series, attention, losses, weather] = await Promise.all([
      fetchJSON("/api/overview", { plant, date }),
      fetchJSON("/api/plant/timeseries", { plant, date }),
      fetchJSON("/api/alerts", { plant, date, status: "Active", sort: "severity", limit: 5, include_notices: false }),
      fetchJSON("/api/losses", { plant }),
      fetchJSON("/api/weather/day", { plant, date }).catch(() => null),   // optional: page works without it
    ]);
    clearError();
    lastData = { overview, series, attention, losses, weather };
    renderAll(lastData);
  } catch (error) {
    showError(error.message);
  }
}

function renderAll({ overview, series, attention, losses, weather }) {
  document.getElementById("takeaway").textContent = overview.takeaway;
  renderKpis(overview);
  renderWeatherMini(weather);
  renderDayChart(overview, series, weather);
  renderAttention(attention);
  renderLossChart(losses);
}

function kpiTile(label, value, compare, status = "") {
  return `<div class="card kpi ${status}">
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
      <div class="kpi-compare">${compare}</div>
    </div>`;
}

// Big number with a small unit, e.g. 1,47,535 kWh (keeps the tile on one line).
const kwhValue = (value) => `${fmt.number(value)}<span class="unit">kWh</span>`;

function renderKpis(o) {
  const gap = o.actual_kwh - o.expected_kwh;
  const alerts = o.active_alerts_by_severity;
  const openCount = SEVERITIES.reduce((sum, level) => sum + (alerts[level] || 0), 0);
  const chips = SEVERITIES.filter((level) => alerts[level] > 0)
    .map((level) => `${severityBadge(`${alerts[level]} ${level}`)}`).join(" ");

  document.getElementById("kpis").innerHTML = [
    kpiTile("Actual energy", kwhValue(o.actual_kwh),
      `${gap >= 0 ? "+" : "−"}${fmt.kwh(Math.abs(gap))} vs expected`),
    kpiTile("Expected energy", kwhValue(o.expected_kwh), "for this day's sunlight & temperature"),
    kpiTile("Energy lost", kwhValue(o.fault_loss_kwh),
      o.at_risk_kwh > 0 ? `+ ${fmt.kwh(o.at_risk_kwh)} at risk (data gaps)` : "from detected faults",
      o.fault_loss_kwh > 0 ? "bad" : "ok"),
    kpiTile("Money lost", fmt.inr(o.fault_loss_inr),
      `at ₹${o.tariff_inr_per_kwh}/kWh`,
      o.fault_loss_inr > 0 ? "bad" : "ok"),
    kpiTile("Open alerts", fmt.number(openCount),
      openCount ? `<div class="chips">${chips}</div>` : "nothing open on this day",
      alerts.Critical > 0 ? "bad" : openCount ? "warn" : "ok"),
  ].join("");
}


/** Weather mini-card: sky, sunshine score, hottest panel, natural (weather) vs fixable (fault) losses. */
function renderWeatherMini(weather) {
  const card = document.getElementById("weather-mini");
  card.hidden = !weather;
  if (!weather) return;
  const d = weather.day;
  const sky = SKY[d.dominant_sky] || { icon: "" };
  card.innerHTML = `
    <span class="wm-icon" id="wm-icon" aria-hidden="true">${sky.icon}</span>
    <div class="wm-stat"><span class="kpi-label"><span id="wm-sky-label">Sky</span></span>
      <strong id="wm-sky">${escapeHTML(d.dominant_sky || "–")} · ${fmt.number(d.sunshine_score)}/100</strong></div>
    <div class="wm-stat"><span class="kpi-label" id="wm-temp-label">Hottest panel</span>
      <strong id="wm-temp">${fmt.number(d.max_module_c)} °C</strong></div>
    <div class="wm-stat"><span class="kpi-label">Weather cost (natural)</span><strong>${fmt.kwh(weather.natural_loss_kwh)}</strong></div>
    <div class="wm-stat"><span class="kpi-label">Faults cost (fixable)</span><strong>${fmt.kwh(weather.fixable_loss_kwh)}</strong></div>
    <a class="wm-link" href="weather.html">Weather & Energy →</a>`;
}

function renderDayChart(overview, series, weather = null) {
  const points = series.points;
  // Sky band above the chart: from the replay ticks themselves, or matched by time from /api/weather/day.
  const skyAt = weather ? Object.fromEntries(weather.points.map((p) => [p.timestamp, p.sky_label])) : {};
  const skyLabels = points.map((p) => (p.sky_label !== undefined ? p.sky_label : skyAt[p.timestamp] || null));
  const hasSky = skyLabels.some(Boolean);
  document.getElementById("day-chart-title").textContent = "Actual vs expected output";
  Charts.draw("day-chart", {
    type: "line",
    data: {
      labels: points.map((p) => fmt.time(p.timestamp)),
      datasets: [
        { label: "Actual (kW)", data: points.map((p) => p.actual_kw), borderColor: Charts.color("--chart-actual"),
          backgroundColor: Charts.color("--chart-actual"), borderWidth: 2, pointRadius: 0, tension: 0.25, yAxisID: "power" },
        { label: "Expected (kW)", data: points.map((p) => p.expected_kw), borderColor: Charts.color("--chart-expected"),
          backgroundColor: Charts.color("--chart-expected"), borderWidth: 2, borderDash: [6, 4], pointRadius: 0,
          tension: 0.25, yAxisID: "power" },
        { label: "Sunlight (irradiation)", data: points.map((p) => p.irradiation), borderColor: Charts.color("--chart-sun"),
          backgroundColor: "transparent", borderWidth: 1.5, pointRadius: 0, tension: 0.25, yAxisID: "sun", fill: false },
      ],
    },
    plugins: hasSky ? [Charts.skyStrip(skyLabels)] : [],
    options: (hasSky ? Charts.skyStripOptions : (o) => o)({
      interaction: { mode: "index", intersect: false },
      scales: {
        x: Charts.axis("Time of day", { ticks: { maxTicksLimit: 12 } }),
        power: Charts.axis("Plant AC power (kW)", { position: "left", beginAtZero: true }),
        sun: Charts.axis("Irradiation (kW/m²)", { position: "right", beginAtZero: true, grid: { drawOnChartArea: false } }),
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: (ctx) => ctx.dataset.yAxisID === "sun"
              ? `Sunlight: ${fmt.number(ctx.parsed.y, 2)}`
              : `${ctx.dataset.label.replace(" (kW)", "")}: ${fmt.number(ctx.parsed.y)} kW`,
            afterBody: (items) => {
              const missing = points[items[0].dataIndex].missing_inverters;
              const sky = skyLabels[items[0].dataIndex];
              return [sky ? `Sky: ${sky}` : "", missing ? `${missing} inverter(s) not reporting` : ""].filter(Boolean);
            },
          },
        },
      },
    }),
  });
}

function renderAttention(attention) {
  const list = document.getElementById("attention");
  if (!attention.alerts.length) {
    list.innerHTML = `<li class="empty">No open alerts on this day ✔</li>`;
    return;
  }
  list.innerHTML = attention.alerts.map((a) => {
    const where = a.inverter === "ALL" ? "Whole plant" : `Inverter ${escapeHTML(a.inverter)}`;
    const impact = a.energy_at_risk_kwh > 0
      ? `${fmt.kwh(a.energy_at_risk_kwh)} at risk`
      : `${fmt.kwh(a.energy_loss_kwh)} lost · ${fmt.inr(a.money_loss_inr)}`;
    const when = a.duration_hours > 24 ? "whole period" : `${fmt.time(a.start)}–${fmt.time(a.end)}`;
    return `<li><a href="alerts.html?id=${encodeURIComponent(a.id)}">
        <div class="list-title">${severityBadge(a.severity)} ${fmt.fault(a.fault_type)}</div>
        <div class="list-meta">${where} · ${when} · ${impact}</div>
      </a></li>`;
  }).join("");
}

function renderLossChart(losses) {
  const rows = losses.by_fault_type.filter((r) => r.fault_loss_kwh > 0 || r.at_risk_kwh > 0);
  const totalLoss = rows.reduce((sum, r) => sum + r.fault_loss_kwh, 0);
  const biggest = rows.slice().sort((a, b) => b.fault_loss_kwh - a.fault_loss_kwh)[0];
  document.getElementById("loss-chart-title").textContent = biggest && totalLoss > 0
    ? `${fmt.pct(biggest.fault_loss_kwh / totalLoss)} of energy lost came from: ${fmt.fault(biggest.fault_type).toLowerCase()}`
    : "Energy lost by fault type";
  Charts.draw("loss-chart", {
    type: "bar",
    data: {
      labels: rows.map((r) => fmt.fault(r.fault_type)),
      datasets: [
        { label: "Confirmed loss (kWh)", data: rows.map((r) => r.fault_loss_kwh), backgroundColor: Charts.color("--bad") },
        { label: "At risk — data gaps (kWh)", data: rows.map((r) => r.at_risk_kwh), backgroundColor: Charts.color("--chart-sun") },
      ],
    },
    options: {
      indexAxis: "y",
      scales: { x: Charts.axis("Energy (kWh)", { stacked: true, beginAtZero: true }), y: { stacked: true } },
      plugins: {
        tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label.replace(" (kWh)", "")}: ${fmt.kwh(ctx.parsed.x)}` } },
      },
    },
  });
}

window.addEventListener("themechange", () => {
  if (typeof Replay !== "undefined") Replay.stop(false);
  if (lastData) renderAll(lastData);
});
Layout.init("overview", loadOverview);
