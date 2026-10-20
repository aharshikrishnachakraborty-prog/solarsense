// Overview page: takeaway, KPI tiles, actual-vs-expected chart, alerts needing attention, loss by fault type.

let lastData = null;   // kept so charts can be redrawn when the theme changes

async function loadOverview(state) {
  const { plant, date } = state;
  if (typeof Replay !== "undefined") Replay.stop(false);   // a new plant/date ends any running replay
  document.getElementById("all-alerts-link").href = `alerts.html?plant=${plant}`;
  try {
    const [overview, series, attention, losses] = await Promise.all([
      fetchJSON("/api/overview", { plant, date }),
      fetchJSON("/api/plant/timeseries", { plant, date }),
      fetchJSON("/api/alerts", { plant, date, status: "Active", sort: "severity", limit: 5, include_notices: false }),
      fetchJSON("/api/losses", { plant }),
    ]);
    clearError();
    lastData = { overview, series, attention, losses };
    renderAll(lastData);
  } catch (error) {
    showError(error.message);
  }
}

function renderAll({ overview, series, attention, losses }) {
  document.getElementById("takeaway").textContent = overview.takeaway;
  renderKpis(overview);
  renderNotices(overview.data_quality_notices);
  renderDayChart(overview, series);
  renderAttention(attention);
  renderLossChart(losses);
}

function kpiTile(label, value, compare, status = "", tip = "") {
  return `<div class="card kpi ${status}">
      <div class="kpi-label">${label}${tip ? infoTip(tip) : ""}</div>
      <div class="kpi-value">${value}</div>
      <div class="kpi-compare">${compare}</div>
    </div>`;
}

// Big number with a small unit, e.g. 1,47,535 kWh (keeps the tile on one line).
const kwhValue = (value) => `${fmt.number(value)}<span class="unit">kWh</span>`;

function renderKpis(o) {
  const pr = o.performance_ratio;
  const prBand = prStatus(pr) === "none" ? "" : prStatus(pr);
  const gap = o.actual_kwh - o.expected_kwh;
  const alerts = o.active_alerts_by_severity;
  const openCount = SEVERITIES.reduce((sum, level) => sum + (alerts[level] || 0), 0);
  const chips = SEVERITIES.filter((level) => alerts[level] > 0)
    .map((level) => `${severityBadge(`${alerts[level]} ${level}`)}`).join(" ");
  const tariffTip = `ASSUMPTION: ₹${o.tariff_inr_per_kwh}/kWh. ${o.tariff_note}`;

  document.getElementById("kpis").innerHTML = [
    kpiTile("Actual energy", kwhValue(o.actual_kwh),
      `${gap >= 0 ? "+" : "−"}${fmt.kwh(Math.abs(gap))} vs expected`),
    kpiTile("Expected energy", kwhValue(o.expected_kwh), "for this day's sunlight & temperature"),
    kpiTile(AVE_LABEL, fmt.pct(pr, 1), "actual ÷ expected energy (100% = as estimated)", prBand, AVE_TIP),
    kpiTile("Energy lost", kwhValue(o.fault_loss_kwh),
      o.at_risk_kwh > 0 ? `+ ${fmt.kwh(o.at_risk_kwh)} at risk (data gaps)` : "from detected faults",
      o.fault_loss_kwh > 0 ? "bad" : "ok"),
    kpiTile("Money lost", fmt.inr(o.fault_loss_inr),
      `at ₹${o.tariff_inr_per_kwh}/kWh (assumed tariff — <a href="about.html">see About</a>)`,
      o.fault_loss_inr > 0 ? "bad" : "ok", tariffTip),
    kpiTile("Open alerts", fmt.number(openCount),
      openCount ? `<div class="chips">${chips}</div>` : "nothing open on this day",
      alerts.Critical > 0 ? "bad" : openCount ? "warn" : "ok"),
  ].join("");
}

/** Plant-wide data-quality notices (no energy lost): one small banner instead of alerts. */
function renderNotices(notices) {
  const box = document.getElementById("notices");
  if (!notices || !notices.length) { box.hidden = true; return; }
  box.hidden = false;
  const first = notices[0].reason;
  const short = first.length > 110 ? `${first.slice(0, first.lastIndexOf(" ", 107))}…` : first;   // cut at a word
  box.innerHTML = `<strong>Data quality notice:</strong> ${notices.length} plant-wide sensor/data issue${notices.length > 1 ? "s" : ""} ` +
    `(no energy lost) — ${escapeHTML(short)} <a href="about.html">Details on the About page →</a>`;
}

function renderDayChart(overview, series) {
  const points = series.points;
  const pr = overview.performance_ratio;
  document.getElementById("day-chart-title").textContent = pr === null
    ? "Actual vs expected output"
    : `Plant made ${fmt.pct(pr)} of the output the weather allowed`;
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
    options: {
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
              return missing ? `${missing} inverter(s) not reporting` : "";
            },
          },
        },
      },
    },
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
