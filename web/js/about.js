// About page: fills in the live assumptions list and the number of days from the API.

async function loadAbout(state) {
  try {
    const assumptions = await fetchJSON("/api/assumptions");
    clearError();
    document.getElementById("assumptions").innerHTML = assumptions.map((a) => `
      <tr>
        <td><strong>${escapeHTML(a.title)}</strong></td>
        <td style="white-space: nowrap">${escapeHTML(a.value)} ${escapeHTML(a.unit)}</td>
        <td>${escapeHTML(a.why)}</td>
        <td class="muted">${escapeHTML(a.source)}</td>
      </tr>`).join("");
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
