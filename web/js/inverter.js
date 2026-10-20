// Inverter page: one inverter's day (actual vs expected vs peers, alerts shaded), its daily trend and its alerts.

const ALERT_SHADE = "rgba(239, 68, 68, 0.14)";
let inverterId = new URLSearchParams(window.location.search).get("id");
let lastInverterData = null;

async function loadInverterPage(state) {
  try {
    // The inverter list comes from the heatmap (all inverters of the chosen plant).
    const { inverters } = await fetchJSON("/api/plant/heatmap", { plant: state.plant });
    if (!inverters.includes(inverterId)) inverterId = inverters[0];
    const select = document.getElementById("inverter-select");
    select.innerHTML = inverters.map((id) => `<option value="${escapeHTML(id)}">${escapeHTML(id)}</option>`).join("");
    select.value = inverterId;
    select.onchange = () => { inverterId = select.value; loadInverterPage(state); };

    const detail = await fetchJSON(`/api/inverter/${encodeURIComponent(inverterId)}`, { date: state.date });
    // Keep the address bar shareable: inverter.html?id=…&date=…&plant=…
    history.replaceState(null, "", `?id=${encodeURIComponent(inverterId)}&date=${state.date}&plant=${state.plant}`);
    clearError();
    lastInverterData = detail;
    renderInverter(detail);
  } catch (error) {
    showError(error.message);
  }
}

function renderInverter(detail) {
  const today = detail.daily_history.find((d) => d.date === detail.date) || {};
  const alertsToday = detail.alerts.filter((a) => alertOverlapsDay(a, detail.date));
  const trend = detail.pr_trend;
  document.getElementById("takeaway").textContent =
    `Inverter ${detail.inverter} (Plant ${detail.plant}) on ${fmt.date(detail.date)}: made ${fmt.pct(today.performance_ratio)} ` +
    `of expected, ${alertsToday.length} alert(s) that day. Over all days its actual-vs-expected trend is ` +
    `${trend ? `${trend.slope_pct_per_day >= 0 ? "+" : ""}${fmt.number(trend.slope_pct_per_day, 2)}% per day` : "unknown"}.`;

  const band = prStatus(today.performance_ratio);
  document.getElementById("kpis").innerHTML = `
    <div class="card"><div class="kpi-label">Actual energy</div><div class="kpi-value">${fmt.number(today.actual_kwh)}<span class="unit">kWh</span></div><div class="kpi-compare">on this day</div></div>
    <div class="card"><div class="kpi-label">Expected energy</div><div class="kpi-value">${fmt.number(today.expected_kwh)}<span class="unit">kWh</span></div><div class="kpi-compare">for this day's sunlight</div></div>
    <div class="card kpi ${band === "none" ? "" : band}"><div class="kpi-label">${AVE_LABEL}${infoTip(AVE_TIP)}</div><div class="kpi-value">${fmt.pct(today.performance_ratio, 1)}</div><div class="kpi-compare">100% = as estimated</div></div>
    <div class="card kpi ${today.fault_loss_kwh > 0 ? "bad" : "ok"}"><div class="kpi-label">Energy lost</div><div class="kpi-value">${fmt.number(today.fault_loss_kwh)}<span class="unit">kWh</span></div><div class="kpi-compare">${fmt.inr(today.fault_loss_inr)} (assumed tariff — <a href="about.html">see About</a>)</div></div>`;

  renderDayChart(detail, alertsToday);
  renderPrChart(detail);
  renderAlertList(detail);
}

function renderDayChart(detail, alertsToday) {
  const series = detail.series;
  const inAlert = series.map((p) => alertsToday.some((a) => p.timestamp >= a.start && p.timestamp < a.end));
  const missing = series.filter((p) => p.is_missing).length;
  document.getElementById("day-title").textContent = alertsToday.length
    ? `${alertsToday.length} alert period(s) on this day — shaded in red`
    : missing ? `${missing} missing readings on this day` : "Inverter followed its expected output all day";
  Charts.draw("day-chart", {
    type: "line",
    data: {
      labels: series.map((p) => fmt.time(p.timestamp)),
      datasets: [
        { label: "Actual (kW)", data: series.map((p) => p.actual_kw), borderColor: Charts.color("--chart-actual"),
          backgroundColor: Charts.color("--chart-actual"), borderWidth: 2, pointRadius: 0, tension: 0.2, spanGaps: false },
        { label: "Expected (kW)", data: series.map((p) => p.expected_kw), borderColor: Charts.color("--chart-expected"),
          backgroundColor: Charts.color("--chart-expected"), borderWidth: 2, borderDash: [6, 4], pointRadius: 0, tension: 0.2 },
        { label: "Peer median (kW)", data: series.map((p) => p.peer_median_kw), borderColor: Charts.color("--chart-sun"),
          backgroundColor: Charts.color("--chart-sun"), borderWidth: 1.5, pointRadius: 0, tension: 0.2 },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: { x: Charts.axis("Time of day", { ticks: { maxTicksLimit: 12 } }),
                y: Charts.axis("AC power (kW)", { beginAtZero: true }) },
      plugins: {
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label.replace(" (kW)", "")}: ${ctx.parsed.y === null ? "no reading" : `${fmt.number(ctx.parsed.y)} kW`}`,
            afterBody: (items) => (inAlert[items[0].dataIndex] ? "⚠ inside an alert period" : ""),
          },
        },
      },
    },
    plugins: [Charts.shade(Charts.rangesFromFlags(inAlert, ALERT_SHADE))],
  });
}

function renderPrChart(detail) {
  const days = detail.daily_history;
  const trend = detail.pr_trend ? Object.fromEntries(detail.pr_trend.points.map((p) => [p.date, p.performance_ratio])) : {};
  const selected = days.map((d) => d.date === detail.date);
  const lowDays = days.filter((d) => prStatus(d.performance_ratio) === "bad").length;
  document.getElementById("pr-title").textContent = `${lowDays} of ${days.length} days below 85% of expected`;
  Charts.draw("pr-chart", {
    type: "line",
    data: {
      labels: days.map((d) => fmt.date(d.date).slice(0, 6)),
      datasets: [
        { label: "Daily actual vs expected (%)", data: days.map((d) => (d.performance_ratio === null ? null : d.performance_ratio * 100)),
          borderColor: Charts.color("--chart-actual"), backgroundColor: Charts.color("--chart-actual"), borderWidth: 2,
          pointRadius: days.map((d, i) => (selected[i] ? 5 : 2)) },
        { label: "Trend line", data: days.map((d) => (trend[d.date] === undefined ? null : trend[d.date] * 100)),
          borderColor: Charts.color("--chart-expected"), backgroundColor: Charts.color("--chart-expected"),
          borderDash: [6, 4], borderWidth: 2, pointRadius: 0 },
        { label: "Unusual day (hint)", data: days.map((d) => (d.is_unusual ? d.performance_ratio * 100 : null)),
          showLine: false, backgroundColor: "#a855f7", borderColor: "#a855f7", pointRadius: 5 },
      ],
    },
    options: {
      scales: { x: Charts.axis("Day"), y: Charts.axis("Actual ÷ expected (%)", { suggestedMin: 0, suggestedMax: 110 }) },
      plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmt.number(ctx.parsed.y, 1)}%` } } },
    },
  });
}

function renderAlertList(detail) {
  document.getElementById("alerts-title").textContent = `Alerts for this inverter (${detail.alerts.length})`;
  const list = document.getElementById("alert-list");
  if (!detail.alerts.length) {
    list.innerHTML = `<li class="empty">No alerts for this inverter ✔</li>`;
    return;
  }
  list.innerHTML = detail.alerts.slice().reverse().map((a) => `
    <li><a href="alerts.html?id=${encodeURIComponent(a.id)}">
      <div class="list-title">${severityBadge(a.severity)} ${fmt.fault(a.fault_type)} <span class="status ${a.status}">${a.status}</span></div>
      <div class="list-meta">${fmt.date(a.start)} ${fmt.time(a.start)}–${fmt.time(a.end)} ·
        ${a.energy_at_risk_kwh > 0 ? `${fmt.kwh(a.energy_at_risk_kwh)} at risk` : `${fmt.kwh(a.energy_loss_kwh)} lost`}</div>
    </a></li>`).join("");
}

window.addEventListener("themechange", () => { if (lastInverterData) renderInverter(lastInverterData); });
Layout.init("inverter", loadInverterPage);
