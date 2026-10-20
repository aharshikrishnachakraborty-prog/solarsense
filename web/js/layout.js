// Builds the shared top bar on every page and remembers the chosen plant, date and theme.

const PAGES = [
  { key: "overview", label: "Overview", href: "index.html" },
  { key: "plant", label: "Plant", href: "plant.html" },
  { key: "inverter", label: "Inverters", href: "inverter.html" },
  { key: "alerts", label: "Alerts", href: "alerts.html" },
  { key: "validation", label: "Validation", href: "validation.html" },
  { key: "about", label: "About", href: "about.html" },
];

const SUN_LOGO = `
  <svg viewBox="0 0 32 32" aria-hidden="true">
    <circle cx="16" cy="16" r="6.5" fill="#f59e0b"/>
    <g stroke="#f59e0b" stroke-width="2.4" stroke-linecap="round">
      <line x1="16" y1="2.5" x2="16" y2="6"/><line x1="16" y1="26" x2="16" y2="29.5"/>
      <line x1="2.5" y1="16" x2="6" y2="16"/><line x1="26" y1="16" x2="29.5" y2="16"/>
      <line x1="6.5" y1="6.5" x2="8.9" y2="8.9"/><line x1="23.1" y1="23.1" x2="25.5" y2="25.5"/>
      <line x1="6.5" y1="25.5" x2="8.9" y2="23.1"/><line x1="23.1" y1="8.9" x2="25.5" y2="6.5"/>
    </g>
  </svg>`;

// localStorage can be blocked (private windows, strict settings) — never let that break the page.
const storage = {
  get(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } },
  set(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* not saved — fine */ } },
};
// Same idea, but forgotten when the browser tab closes (used for the replay date).
const session = {
  get(key) { try { return window.sessionStorage.getItem(key); } catch (e) { return null; } },
  set(key, value) { try { window.sessionStorage.setItem(key, value); } catch (e) { /* not saved — fine */ } },
};

function applySavedTheme() {
  const theme = storage.get("solarsense-theme");
  if (theme) document.documentElement.setAttribute("data-theme", theme);
}
applySavedTheme();   // run immediately so the page does not flash the wrong theme

const Layout = {
  state: { plant: null, date: null, plants: [], dates: [] },

  /** Draw the top bar, load plants/dates, then call onChange(state) now and whenever a selector changes. */
  async init(activePage, onChange = null) {
    const header = document.getElementById("topbar");
    header.className = "topbar";
    header.innerHTML = `
      <a class="brand" href="index.html">${SUN_LOGO}<span>SolarSense</span></a>
      <nav class="nav" aria-label="Main">
        ${PAGES.map((p) => `<a href="${p.href}" class="${p.key === activePage ? "active" : ""}">${p.label}</a>`).join("")}
      </nav>
      <div class="controls">
        <label for="plant-select">Plant</label>
        <select id="plant-select" aria-label="Plant"></select>
        <label for="date-select">Replay date</label>
        <select id="date-select" aria-label="Replay date"></select>
        <button id="theme-toggle" class="icon-btn" title="Switch light / dark theme" aria-label="Switch theme">◐</button>
      </div>`;
    document.getElementById("theme-toggle").addEventListener("click", Layout.toggleTheme);

    let info;
    try {
      info = await fetchJSON("/api/plants");
    } catch (error) {
      showError(error.message);
      return null;
    }
    const state = Layout.state;
    state.plants = info.plants.map((p) => p.plant);
    state.dates = info.dates;
    // Each plant's highest-loss day is its default replay date (the most useful day to look at).
    const worstDay = Object.fromEntries(info.plants.map((p) => [p.plant, p.worst_loss_date]));

    // Plant: URL (?plant=2) → remembered → default.
    // Date: URL (?date=…) → chosen earlier in THIS browser session → the plant's highest-loss day.
    const url = new URLSearchParams(window.location.search);
    const savedPlant = Number(url.get("plant") || storage.get("solarsense-plant"));
    state.plant = state.plants.includes(savedPlant) ? savedPlant : info.default_plant;
    const savedDate = url.get("date") || session.get(`solarsense-date-${state.plant}`);
    state.date = state.dates.includes(savedDate) ? savedDate : worstDay[state.plant];
    if (url.get("date") === state.date) session.set(`solarsense-date-${state.plant}`, state.date);

    const plantSelect = document.getElementById("plant-select");
    const dateSelect = document.getElementById("date-select");
    plantSelect.innerHTML = info.plants
      .map((p) => `<option value="${p.plant}">Plant ${p.plant} (${p.inverters} inverters)</option>`).join("");
    const fillDates = () => {
      dateSelect.innerHTML = state.dates.map((d) =>
        `<option value="${d}">${fmt.date(d)}${d === worstDay[state.plant] ? " (highest loss)" : ""}</option>`).join("");
      dateSelect.value = state.date;
    };
    plantSelect.value = state.plant;
    fillDates();

    plantSelect.addEventListener("change", () => {
      state.plant = Number(plantSelect.value);
      storage.set("solarsense-plant", state.plant);
      // A new plant opens on its own highest-loss day (unless a day was already picked for it this session).
      const picked = session.get(`solarsense-date-${state.plant}`);
      state.date = state.dates.includes(picked) ? picked : worstDay[state.plant];
      fillDates();
      if (onChange) onChange(state);
    });
    dateSelect.addEventListener("change", () => {
      state.date = dateSelect.value;
      session.set(`solarsense-date-${state.plant}`, state.date);
      if (onChange) onChange(state);
    });
    if (onChange) onChange(state);
    return state;
  },

  toggleTheme() {
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    const next = dark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    storage.set("solarsense-theme", next);
    window.dispatchEvent(new Event("themechange"));   // charts redraw with the new colours
  },
};
