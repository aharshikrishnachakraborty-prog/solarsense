// Alert detail side panel: reason, "Why?" evidence chart, key numbers, loss, action, Acknowledge / Resolve.

const EVIDENCE_LABELS = {   // friendly names for evidence numbers (anything not listed is skipped)
  avg_irradiation: ["Average sunlight (irradiation)", (v) => fmt.number(v, 2)],
  avg_actual_kw: ["Average actual power", (v) => `${fmt.number(v)} kW`],
  avg_expected_kw: ["Average expected power", (v) => `${fmt.number(v)} kW`],
  avg_residual_pct: ["Below expected by", (v) => `${fmt.number(-v)}%`],
  avg_peer_ratio: ["Output vs neighbours", (v) => `${fmt.pct(v)} of theirs`],
  others_down_pct: ["Other inverters down at same time", (v) => `${fmt.number(v)}%`],
  intervals: ["15-minute readings affected", (v) => fmt.number(v)],
  slope_pct_per_day: ["Trend per day", (v) => `${fmt.number(v, 2)}%`],
  total_decline_pct: ["Total decline", (v) => `${fmt.number(v, 1)}%`],
  avg_temp_delta_c: ["Panel hotter than air by", (v) => `${fmt.number(v, 1)} °C`],
};

const AlertPanel = {
  onChange: null,

  /** Fetch one alert and show it in the side panel. */
  async open(id, onChange) {
    AlertPanel.onChange = onChange;
    const root = document.getElementById("panel-root");
    root.innerHTML = `<div class="backdrop" data-close></div>
      <aside class="drawer" role="dialog" aria-modal="true" aria-label="Alert detail"><div class="skeleton" style="height: 300px"></div></aside>`;
    root.querySelector("[data-close]").addEventListener("click", AlertPanel.close);
    document.addEventListener("keydown", AlertPanel.onKey);
    history.replaceState(null, "", `?id=${encodeURIComponent(id)}`);
    try {
      AlertPanel.render(await fetchJSON(`/api/alerts/${encodeURIComponent(id)}`));
    } catch (error) {
      root.querySelector(".drawer").innerHTML = `<div class="error-banner">${error.message}</div>
        <button data-close-btn>Close</button>`;
      root.querySelector("[data-close-btn]").addEventListener("click", AlertPanel.close);
    }
  },

  close() {
    document.getElementById("panel-root").innerHTML = "";
    document.removeEventListener("keydown", AlertPanel.onKey);
    history.replaceState(null, "", window.location.pathname);
  },

  onKey(event) { if (event.key === "Escape") AlertPanel.close(); },

  render(a) {
    const drawer = document.querySelector("#panel-root .drawer");
    const where = a.inverter === "ALL" ? `Plant ${a.plant} — whole plant`
      : `Plant ${a.plant} · <a href="inverter.html?id=${encodeURIComponent(a.inverter)}&date=${a.start.slice(0, 10)}&plant=${a.plant}">Inverter ${escapeHTML(a.inverter)}</a>`;
    const when = a.duration_hours > 24 ? "whole period" : `${fmt.date(a.start)}, ${fmt.time(a.start)}–${fmt.time(a.end)} (${fmt.number(a.duration_hours, 2)} h)`;
    const facts = Object.entries(EVIDENCE_LABELS)
      .filter(([key]) => a.evidence[key] !== undefined && a.evidence[key] !== null)
      .map(([key, [label, format]]) => `<div class="fact"><div class="kpi-label">${label}</div><strong>${format(a.evidence[key])}</strong></div>`);
    const lossFacts = a.energy_at_risk_kwh > 0
      ? `<div class="fact"><div class="kpi-label">Energy at risk (not confirmed)</div><strong>${fmt.kwh(a.energy_at_risk_kwh)}</strong></div>
         <div class="fact"><div class="kpi-label">Money at risk ${infoTip(a.tariff_note)}</div><strong>${fmt.inr(a.money_at_risk_inr)}</strong></div>`
      : `<div class="fact"><div class="kpi-label">Energy lost</div><strong>${fmt.kwh(a.energy_loss_kwh)}</strong></div>
         <div class="fact"><div class="kpi-label">Money lost ${infoTip(a.tariff_note)}</div><strong>${fmt.inr(a.money_loss_inr)}</strong></div>`;

    drawer.innerHTML = `
      <div class="drawer-head">
        <div>
          <div class="list-title">${severityBadge(a.severity)} ${fmt.fault(a.fault_type)}</div>
          <div class="muted">${escapeHTML(a.id)} · ${where}</div>
          <div class="muted">${when}</div>
        </div>
        <button class="icon-btn" data-close-btn aria-label="Close">✕</button>
      </div>
      <h2>Why?</h2>
      <p>${escapeHTML(a.reason)}</p>
      ${a.series_kind === "none" ? `<p class="muted">This is a plant-wide data issue — there is no power curve to show.</p>`
        : `<div class="chart-box small"><canvas id="evidence-chart" aria-label="Evidence chart"></canvas></div>`}
      <div class="facts">${lossFacts}${facts.join("")}</div>
      <div class="action-box"><strong>Recommended action:</strong> ${escapeHTML(a.recommended_action)}</div>
      <div>Status: <span id="panel-status" class="status ${a.status}">${a.status}</span>
        ${a.status_updated_at ? `<span class="muted">(changed ${escapeHTML(a.status_updated_at.replace("T", " "))})</span>` : ""}</div>
      <div class="btn-row">
        <button class="btn-primary" data-status="Acknowledged">Acknowledge</button>
        <button data-status="Resolved">Resolve</button>
        <button data-status="Open">Re-open</button>
      </div>`;
    drawer.querySelector("[data-close-btn]").addEventListener("click", AlertPanel.close);
    drawer.querySelectorAll("[data-status]").forEach((button) =>
      button.addEventListener("click", () => AlertPanel.setStatus(a.id, button.dataset.status)));
    if (a.series_kind !== "none") AlertPanel.drawEvidence(a);
  },

  drawEvidence(a) {
    const s = a.series;
    if (a.series_kind === "daily") {
      Charts.draw("evidence-chart", { type: "line", data: { labels: s.map((p) => fmt.date(p.date).slice(0, 6)),
        datasets: [{ label: "Daily actual vs expected (%)", data: s.map((p) => p.performance_ratio * 100),
          borderColor: Charts.color("--chart-actual"), pointRadius: 2 }] },
        options: { scales: { x: Charts.axis("Day"), y: Charts.axis("Actual ÷ expected (%)") } } });
      return;
    }
    const datasets = [
      { label: "Actual (kW)", data: s.map((p) => p.actual_kw), borderColor: Charts.color("--chart-actual"),
        backgroundColor: Charts.color("--chart-actual"), borderWidth: 2, pointRadius: 0 },
      { label: "Expected (kW)", data: s.map((p) => p.expected_kw), borderColor: Charts.color("--chart-expected"),
        backgroundColor: Charts.color("--chart-expected"), borderWidth: 2, borderDash: [6, 4], pointRadius: 0 },
    ];
    if (s.length && "peer_median_kw" in s[0]) {
      datasets.push({ label: "Peer median (kW)", data: s.map((p) => p.peer_median_kw), borderColor: Charts.color("--chart-sun"),
        backgroundColor: Charts.color("--chart-sun"), borderWidth: 1.5, pointRadius: 0 });
    }
    Charts.draw("evidence-chart", {
      type: "line",
      data: { labels: s.map((p) => fmt.time(p.timestamp)), datasets },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: { x: Charts.axis("Time (red = alert period)", { ticks: { maxTicksLimit: 8 } }),
                  y: Charts.axis("AC power (kW)", { beginAtZero: true }) },
        plugins: { tooltip: { callbacks: { label: (ctx) =>
          `${ctx.dataset.label.replace(" (kW)", "")}: ${ctx.parsed.y === null ? "no reading" : `${fmt.number(ctx.parsed.y)} kW`}` } } },
      },
      plugins: [Charts.shade(Charts.rangesFromFlags(s.map((p) => p.in_alert), "rgba(239, 68, 68, 0.14)"))],
    });
  },

  async setStatus(id, status) {
    try {
      const saved = await postJSON(`/api/alerts/${encodeURIComponent(id)}/status`, { status });
      const label = document.getElementById("panel-status");
      label.className = `status ${saved.status}`;
      label.textContent = saved.status;
      if (AlertPanel.onChange) AlertPanel.onChange(id, saved.status);
    } catch (error) {
      showError(error.message);
    }
  },
};
