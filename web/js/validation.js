// Validation page: results of the injected-fault test (all numbers from /api/validation).

const FAULT_LABELS = { trip: "Inverter trip", underperformance: "Underperformance", data_gap: "Data gap", soiling: "Soiling (slow decline)" };
const FAULT_ORDER = ["trip", "data_gap", "underperformance", "soiling"];
let validationData = null;

/** "[0.6, 0.7)" → "keeps 60–70%" or "1–2 h" — display text only. `largest` = biggest planted size (from the API). */
function bucketLabel(bucket, unit, largest) {
  const [low, rawHigh] = bucket.replace(/[\[\]()]/g, "").split(",").map(Number);
  const high = Math.min(rawHigh, largest);   // the last group's edge is padded a little; show the real largest size
  const trim = (n) => fmt.number(n, 2).replace(/\.?0+$/, "");
  if (unit === "output kept") return `keeps ${Math.round(low * 100)}–${Math.round(high * 100)}%`;
  if (unit === "hours") return `${trim(low)}–${trim(high)} h`;
  return `${trim(low)}–${trim(high)} ${unit}`;
}

function renderValidation(v) {
  const faults = FAULT_ORDER.filter((f) => v.by_fault[f]);
  const results = faults.map((f) => v.by_fault[f]);
  document.getElementById("method").textContent =
    `${v.method} Test days: ${fmt.date(v.test_dates[0])} – ${fmt.date(v.test_dates[1])}; ${fmt.number(v.clean_inverter_days)} healthy inverter-days available.`;
  const best = results.filter((r) => r.recall_pct === 100).length;
  document.getElementById("recall-title").textContent =
    `${best} of ${results.length} fault types caught every time — underperformance and soiling are harder`;

  Charts.draw("recall-chart", {
    data: {
      labels: faults.map((f) => FAULT_LABELS[f]),
      datasets: [
        { type: "bar", label: "Caught (%)", data: results.map((r) => r.recall_pct), backgroundColor: Charts.color("--ok"), yAxisID: "pct" },
        { type: "line", label: "False alarms (count)", data: results.map((r) => r.false_alarms), showLine: false,
          pointRadius: 7, backgroundColor: Charts.color("--bad"), borderColor: Charts.color("--bad"), yAxisID: "count" },
      ],
    },
    options: {
      scales: {
        x: Charts.axis("Planted fault type"),
        pct: Charts.axis("Caught (%)", { min: 0, max: 100 }),
        count: Charts.axis("False alarms", { position: "right", beginAtZero: true, grid: { drawOnChartArea: false } }),
      },
      plugins: { tooltip: { callbacks: { label: (ctx) => ctx.dataset.yAxisID === "pct"
        ? `Caught: ${ctx.parsed.y}% of ${results[ctx.dataIndex].injections}` : `False alarms: ${ctx.parsed.y}` } } },
    },
  });

  const under = v.by_fault.underperformance;
  const buckets = Object.entries(under.recall_by_size_pct);
  const largestKept = v.fault_sizes.underperformance_output_kept[1];
  const smallest = buckets[buckets.length - 1];
  document.getElementById("size-title").textContent =
    `When output only drops a little (${bucketLabel(smallest[0], under.size_unit, largestKept)}), we catch ${smallest[1].recall_pct}%`;
  Charts.draw("size-chart", {
    type: "bar",
    data: { labels: buckets.map(([b]) => bucketLabel(b, under.size_unit, largestKept)),
            datasets: [{ label: "Caught (%)", data: buckets.map(([, s]) => s.recall_pct), backgroundColor: buckets.map(([, s]) =>
              Charts.color(s.recall_pct >= 90 ? "--ok" : s.recall_pct >= 50 ? "--warn" : "--bad")) }] },
    options: {
      scales: { x: Charts.axis("Size of planted fault (output the inverter still kept)"), y: Charts.axis("Caught (%)", { min: 0, max: 100 }) },
      plugins: { legend: { display: false },
                 tooltip: { callbacks: { label: (ctx) => `Caught ${ctx.parsed.y}% of ${buckets[ctx.dataIndex][1].injections} planted faults` } } },
    },
  });

  document.getElementById("results").innerHTML = faults.map((f) => {
    const r = v.by_fault[f];
    return `<tr><td><strong>${FAULT_LABELS[f]}</strong></td><td class="num">${r.injections}</td>
      <td class="num">${r.caught} (${r.recall_pct}%)</td><td class="num">${r.caught_as_other_type}</td><td class="num">${r.missed}</td>
      <td class="num">${r.false_alarms}</td><td class="num">${r.precision_pct}%</td>
      <td class="num">${r.avg_delay_minutes === null ? "end of period" : `${fmt.number(r.avg_delay_minutes)} min`}</td>
      <td class="num">${r.loss_error_median_abs_pct === null ? "–" : `${r.loss_error_median_abs_pct}%`}</td></tr>`;
  }).join("");

  const trade = v.threshold_tradeoff.filter((t) => t.fault === "underperformance");
  const sensitive = trade.find((t) => t.setting === "sensitive");
  document.getElementById("tradeoff-title").textContent =
    `Most sensitive setting catches ${sensitive.recall_pct}% but raises ${sensitive.false_alarms_on_clean_days} false alarms`;
  Charts.draw("tradeoff-chart", {
    data: {
      labels: trade.map((t) => t.setting[0].toUpperCase() + t.setting.slice(1)),
      datasets: [
        { type: "bar", label: "Caught (%)", data: trade.map((t) => t.recall_pct), backgroundColor: Charts.color("--ok"), yAxisID: "pct" },
        { type: "bar", label: "False alarms on healthy days", data: trade.map((t) => t.false_alarms_on_clean_days),
          backgroundColor: Charts.color("--bad"), yAxisID: "count" },
      ],
    },
    options: {
      scales: {
        x: Charts.axis("Threshold setting"),
        pct: Charts.axis("Caught (%)", { min: 0, max: 100 }),
        count: Charts.axis("False alarms", { position: "right", beginAtZero: true, grid: { drawOnChartArea: false } }),
      },
    },
  });

  document.getElementById("caveats").innerHTML = [v.caveat, v.soiling_note,
    "Planted faults are cleaner than real ones (sharp start and end), so real-world detection may be lower."]
    .map((text) => `<li>${escapeHTML(text)}</li>`).join("");

  const ex = v.example_chart;
  if (ex) {
    document.getElementById("example-img").src = `figures/${ex.file.split("/").pop()}`;   // relative: works in a sub-folder too
    document.getElementById("example-caption").textContent =
      `Plant ${ex.plant}, inverter ${ex.inverter}, ${fmt.date(ex.date)}: we cut output to ${ex.output_kept_pct}%. ` +
      `The detector raised an underperformance alert and estimated ${fmt.kwh(ex.estimated_kwh)} lost (true planted loss: ${fmt.kwh(ex.true_kwh)}).`;
  }
}

async function loadValidation() {
  try {
    validationData = await fetchJSON("/api/validation");
    if (!validationData.by_fault) throw new Error("No validation results yet — run: python -m engine.validate");
    clearError();
    renderValidation(validationData);
  } catch (error) {
    showError(error.message);
  }
}

window.addEventListener("themechange", () => { if (validationData) renderValidation(validationData); });
Layout.init("validation").then(loadValidation);
