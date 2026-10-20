// About page: fills in the live assumptions list and the number of days from the API.

async function loadAbout(state) {
  try {
    const [assumptions, settings] = await Promise.all([fetchJSON("/api/assumptions"), fetchJSON("/api/settings")]);
    clearError();
    document.getElementById("assumptions").innerHTML = assumptions.map((a) => `
      <tr>
        <td><strong>${escapeHTML(a.title)}</strong></td>
        <td style="white-space: nowrap">${escapeHTML(a.value)} ${escapeHTML(a.unit)}</td>
        <td>${escapeHTML(a.why)}</td>
        <td class="muted">${escapeHTML(a.source)}</td>
      </tr>`).join("");
    document.getElementById("lim-small").textContent =
      `Small underperformance (output dropping by less than ${fmt.number(settings.underperformance_drop_pct)}% ` +
      "below expected) is usually not caught, by design, to avoid false alarms.";
    if (state) {
      document.getElementById("lim-days").textContent =
        `Only ${state.dates.length} days of data (${fmt.date(state.dates[0])} – ${fmt.date(state.dates[state.dates.length - 1])}), ` +
        "all in one season; accuracy in winter or monsoon is unknown.";
    }
  } catch (error) {
    showError(error.message);
  }
}

Layout.init("about").then(loadAbout);
